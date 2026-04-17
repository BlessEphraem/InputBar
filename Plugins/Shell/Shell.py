import os
import json
import shlex
import subprocess
from rapidfuzz import process, fuzz

from Core.Logging import eprint as _eprint
from Core.Paths import PLUGINS_DATA_DIR as _PLUGINS_DATA_DIR

_SHELL_DATA_DIR = os.path.join(_PLUGINS_DATA_DIR, "Shell")

FAVORITES     = {}
DEFAULT_SHELL = "cmd"
DEFAULT_ICON  = ""

# Custom shells defined by the user in default_shell.json under "extra_shells".
# Key  : alias used in default_shell or as per-entry prefix in favorites.data
# Value: list [executable, arg1, arg2, ...] — the command is appended at the end
# Example: {"wezterm": ["wezterm.exe", "start", "--", "cmd.exe", "/k"]}
EXTRA_SHELLS: dict[str, list[str]] = {}

# First-word prefixes that indicate a shell command when followed by arguments
_CLI_PREFIXES = {
    "python", "python3", "node", "npm", "npx", "git", "pip", "pip3",
    "cargo", "go", "java", "dotnet", "ruby", "perl", "bash", "sh",
    "pwsh", "powershell", "cmd", "code", "nvim", "vim",
}

# Built-in shell names recognised as per-entry prefix in favorites.data.
# Extra shells defined in default_shell.json are checked dynamically via EXTRA_SHELLS.
_KNOWN_SHELLS = {"cmd", "pwsh", "pwsh.exe", "powershell", "powershell.exe"}

_PYTHON_EXECUTABLES = {"python", "python3", "pythonw", "pythonw3"}

# PyInstaller pollutes the child environment with variables that break the
# system Python (PYTHONHOME points to the bundle, TCL_LIBRARY to bundled tcl…).
# Strip them so subprocesses see a clean system environment.
_PYINSTALLER_VARS = {
    "PYTHONHOME", "PYTHONPATH",
    "TCL_LIBRARY", "TK_LIBRARY",
    "_MEIPASS", "_MEIPASS2",
    "PYINSTALLER_PARENT_PID",
}


# ─────────────────────────────────────────────────────
#  Config loaders
# ─────────────────────────────────────────────────────

def _load_default_shell() -> None:
    global DEFAULT_SHELL, DEFAULT_ICON, EXTRA_SHELLS
    shell_file = os.path.join(_SHELL_DATA_DIR, "default_shell.json")
    if os.path.exists(shell_file):
        try:
            with open(shell_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            shell = data.get("default_shell", "cmd")
            DEFAULT_SHELL = shell.strip() if isinstance(shell, str) and shell.strip() else "cmd"

            icon = data.get("default_icon", "")
            DEFAULT_ICON  = icon.strip() if isinstance(icon, str) else ""

            # Extra (custom) shells: {"alias": ["exe", "arg1", ...]}
            extras = data.get("extra_shells", {})
            EXTRA_SHELLS = {}
            if isinstance(extras, dict):
                for name, args in extras.items():
                    if isinstance(name, str) and isinstance(args, list) and args:
                        EXTRA_SHELLS[name.lower()] = [str(a) for a in args]

        except Exception:
            DEFAULT_SHELL = "cmd"
            DEFAULT_ICON  = ""
            EXTRA_SHELLS  = {}
    else:
        DEFAULT_SHELL = "cmd"
        DEFAULT_ICON  = ""
        EXTRA_SHELLS  = {}


def _load_favorites() -> None:
    """Loads favorites.data (key=value shell command pairs)."""
    global FAVORITES
    FAVORITES.clear()

    favorites_file = os.path.join(_SHELL_DATA_DIR, "favorites.data")

    if not os.path.exists(favorites_file):
        return

    try:
        with open(favorites_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    FAVORITES[key.strip().lower()] = value.strip()
    except Exception as e:
        _eprint(f"Shell Plugin: Unable to load favorites.data ({e})")


# ─────────────────────────────────────────────────────
#  Shell command helpers
# ─────────────────────────────────────────────────────

def _clean_env() -> dict:
    env = os.environ.copy()
    for var in _PYINSTALLER_VARS:
        env.pop(var, None)
    return env


def _is_shell_command(value: str) -> bool:
    """
    Returns True when value looks like a shell command (not a bare app name).

    Detection rules (global mode — user has NOT typed the "shell" keyword):
      - Contains a path separator (\\ or /) AND has at least one alphanumeric character
        → avoids triggering on a lone "/" or "\\" typed mid-word
      - Starts with a known CLI prefix AND has at least one argument
        → "git status" triggers, bare "git" does not
    """
    if not value:
        return False

    has_backslash = '\\' in value
    has_slash     = '/' in value and not value.startswith('shell:')

    # Path-separator rule: require meaningful content alongside the slash
    if (has_backslash or has_slash) and any(c.isalnum() for c in value):
        return True

    # CLI-prefix rule: prefix + at least one argument
    parts = value.split()
    if len(parts) > 1 and parts[0].lower() in _CLI_PREFIXES:
        return True

    return False


def _parse_shell_and_cmd(value: str) -> tuple:
    """
    Checks whether the value starts with a known shell name (built-in or extra).
    Returns (shell_override, command):
      - shell_override: the shell alias if found, else None (→ use DEFAULT_SHELL)
      - command: the remainder (or the full value if no shell prefix)
    """
    parts = value.split(None, 1)
    if parts:
        first = parts[0].lower()
        if first in _KNOWN_SHELLS or first in EXTRA_SHELLS:
            cmd = parts[1] if len(parts) > 1 else ""
            return first, cmd
    return None, value


def _parse_cwd(parts: list) -> str | None:
    """
    Given a parsed command (list of tokens), returns the directory of the first
    .py/.pyw argument that exists on disk — used as the working directory so that
    scripts with relative imports/file paths work correctly.
    """
    for part in parts[1:]:
        p = part.strip('"').strip("'")
        if p.lower().endswith((".py", ".pyw")) and os.path.isfile(p):
            return os.path.dirname(os.path.abspath(p))
    return None


def _launch_shell_command(cmd: str, shell_override: str | None = None) -> None:
    """
    Executes cmd via the configured default shell (or shell_override if provided).

    Shell resolution order:
      1. shell_override (from per-entry prefix in favorites.data or inline prefix)
      2. DEFAULT_SHELL from default_shell.json
      3. Falls back to cmd on error

    Extra shells defined in default_shell.json["extra_shells"] are supported:
      The command is appended to the configured args list, e.g.
        wezterm: ["wezterm.exe", "start", "--", "cmd.exe", "/k"] + [cmd]

    Uses conhost.exe for cmd to bypass Windows Terminal (which otherwise hijacks
    CREATE_NEW_CONSOLE and opens a PS7 tab on some WT configurations).
    For Python scripts the CWD is set to the script's directory automatically.
    """
    # Reload config to ensure we have the latest EXTRA_SHELLS and FAVORITES
    _load_default_shell()
    _load_favorites()

    shell = (shell_override if shell_override else DEFAULT_SHELL).lower()

    # Default CWD to user home — avoids inheriting InputBar's own working
    # directory (src/ in dev, the install folder in compiled mode).
    # Overridden to the script's directory when launching a Python file.
    cwd   = os.path.expanduser("~")
    parts = []
    try:
        parts = shlex.split(cmd, posix=False)
        exe   = os.path.splitext(parts[0].lower())[0] if parts else ""
        if exe in _PYTHON_EXECUTABLES:
            script_cwd = _parse_cwd(parts)
            if script_cwd:
                cwd = script_cwd
    except Exception:
        pass

    env = _clean_env()

    CREATE_NEW_CONSOLE = 0x00000010

    # ── Extra (custom) shell ─────────────────────────────────────────────
    if shell in EXTRA_SHELLS:
        if not cmd:
            # If no command is provided, just launch the executable (first item)
            launch_args = [EXTRA_SHELLS[shell][0]]
        else:
            launch_args = EXTRA_SHELLS[shell] + [cmd]
            
        try:
            # 0x08000000 is CREATE_NO_WINDOW, prevents an empty console window from appearing
            subprocess.Popen(launch_args, cwd=cwd, env=env, creationflags=0x08000000)
        except Exception as e:
            _eprint(f"Shell Plugin: Failed to launch via '{shell}' ({e})")
        return

    # ── Built-in shells ──────────────────────────────────────────────────
    # Pass commands as STRING to CreateProcess (not list) to avoid list2cmdline
    # adding extra quotes around tokens that already contain quoted paths.
    try:
        if shell == "cmd":
            subprocess.Popen(f'conhost.exe -- cmd.exe /k "title Command Prompt & {cmd}"',
                             cwd=cwd, env=env)
        elif shell in ("pwsh", "pwsh.exe"):
            subprocess.Popen(
                f'pwsh.exe -NoExit -Command {cmd}',
                creationflags=CREATE_NEW_CONSOLE, cwd=cwd, env=env)
        elif shell in ("powershell", "powershell.exe"):
            subprocess.Popen(
                f'powershell.exe -NoExit -Command {cmd}',
                creationflags=CREATE_NEW_CONSOLE, cwd=cwd, env=env)
        else:
            # Unknown shell name: attempt a generic launch
            subprocess.Popen(
                f'{shell} {cmd}',
                creationflags=CREATE_NEW_CONSOLE, cwd=cwd, env=env)
    except FileNotFoundError:
        _eprint(f"Shell Plugin: shell '{shell}' not found, falling back to cmd.")
        subprocess.Popen(f'conhost.exe -- cmd.exe /k {cmd}', cwd=cwd, env=env)
    except Exception as e:
        _eprint(f"Shell Plugin: Failed to launch '{cmd}' ({e})")


# ─────────────────────────────────────────────────────
#  Favorites search
# ─────────────────────────────────────────────────────

def _get_bundled_icon_path() -> str:
    """Returns the path to shell.svg — always next to Shell.py, in dev and frozen mode."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "shell.svg")


def _icon_fields() -> dict:
    """
    Returns icon-related fields for a Shell result.
    Priority: user's custom DEFAULT_ICON → bundled shell.svg → settings fallback.
    """
    if DEFAULT_ICON and os.path.exists(DEFAULT_ICON):
        return {"icon_type": "file", "exe_path": DEFAULT_ICON}
    bundled = _get_bundled_icon_path()
    if os.path.exists(bundled):
        return {"icon_path": bundled}
    return {"icon_type": "shell"}


def _build_favorite_entry(key: str, score: float) -> dict:
    """Builds a result dict for a single favorites.data entry."""
    value = FAVORITES[key]
    shell_override, actual_cmd = _parse_shell_and_cmd(value)
    return {
        "name":   key,
        "score":  score,
        "action": lambda c=actual_cmd, s=shell_override: _launch_shell_command(c, s),
        **_icon_fields(),
    }


def _search_favorites(query_lower: str) -> list:
    """Multi-pass fuzzy search over favorites.data keys."""
    if not FAVORITES:
        return []

    keys    = list(FAVORITES.keys())
    results = []
    seen    = set()

    # Pass 1: exact key match
    if query_lower in FAVORITES:
        seen.add(query_lower)
        results.append(_build_favorite_entry(query_lower, 100.0))

    # Pass 2: key starts with query (prefix)
    for key in keys:
        if key in seen:
            continue
        if key.startswith(query_lower):
            seen.add(key)
            results.append(_build_favorite_entry(key, 92.0))

    # Pass 3: query is a substring of the key
    if len(query_lower) >= 2:
        for key in keys:
            if key in seen:
                continue
            if query_lower in key:
                seen.add(key)
                results.append(_build_favorite_entry(key, 85.0))

    # Pass 4: fuzzy WRatio
    if len(query_lower) >= 2:
        for key, score, _ in process.extract(query_lower, keys,
                                              scorer=fuzz.WRatio, limit=10):
            if key in seen or score < 50:
                continue
            seen.add(key)
            results.append(_build_favorite_entry(key, score * 0.9))

    return results



# ─────────────────────────────────────────────────────
#  Initialisation
# ─────────────────────────────────────────────────────

_load_default_shell()
_load_favorites()


# ─────────────────────────────────────────────────────
#  on_search entry point
# ─────────────────────────────────────────────────────

def on_search(text: str, is_strict: bool = False) -> list:
    """
    is_strict=True  : user explicitly typed the "shell" keyword.
                      Any non-empty text is always offered as a runnable command,
                      regardless of whether it matches the global detection rules.
    is_strict=False : global mode — only commands that pass _is_shell_command()
                      are offered (avoids polluting results for every search).
    """
    query       = text.strip()
    query_lower = query.lower()

    # ── Empty query ("shell" typed alone) → list all favorites ──────────
    if not query:
        results = [_build_favorite_entry(k, 80.0) for k in FAVORITES.keys()]
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    results = []

    # ── 1. Favorites (fuzzy search over favorites.data keys) ──────────────
    results.extend(_search_favorites(query_lower))

    # ── 2. Direct shell command ───────────────────────────────────────────
    # Strict mode: user explicitly typed "shell <cmd>" → always runnable.
    # Global mode: apply detection rules to avoid false positives.
    if is_strict or _is_shell_command(query):
        _s_override, _actual = _parse_shell_and_cmd(query)
        results.append({
            "name":   f"Shell: {query}",
            "score":  2000,
            "action": lambda c=_actual, s=_s_override: _launch_shell_command(c, s),
            **_icon_fields(),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    seen_names: set = set()
    deduped = []
    for r in results:
        if r["name"] not in seen_names:
            seen_names.add(r["name"])
            deduped.append(r)

    return deduped
