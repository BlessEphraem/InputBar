import os
import json
import shlex
import subprocess
import threading
from rapidfuzz import process, fuzz

from Core.Logging import eprint as _eprint
from Core.Paths import PLUGINS_DATA_DIR as _PLUGINS_DATA_DIR

_SHELL_DATA_DIR = os.path.join(_PLUGINS_DATA_DIR, "Shell")

FAVORITES     = {}
DEFAULT_SHELL = "cmd"
DEFAULT_ICON  = ""

# First-word prefixes that indicate a shell command when followed by arguments
_CLI_PREFIXES = {
    "python", "python3", "node", "npm", "npx", "git", "pip", "pip3",
    "cargo", "go", "java", "dotnet", "ruby", "perl", "bash", "sh",
    "pwsh", "powershell", "cmd", "code", "nvim", "vim",
}

# Shell names that can be used as a per-entry prefix in favorites.data to
# override the default shell for that specific entry.
# Format:  key=<shell> <command>
# Example: btop=cmd btop
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
    global DEFAULT_SHELL, DEFAULT_ICON
    shell_file = os.path.join(_SHELL_DATA_DIR, "default_shell.json")
    if os.path.exists(shell_file):
        try:
            with open(shell_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            shell = data.get("default_shell", "cmd")
            DEFAULT_SHELL = shell.strip() if isinstance(shell, str) and shell.strip() else "cmd"
            icon = data.get("default_icon", "")
            DEFAULT_ICON  = icon.strip() if isinstance(icon, str) else ""
        except Exception:
            DEFAULT_SHELL = "cmd"
            DEFAULT_ICON  = ""
    else:
        DEFAULT_SHELL = "cmd"
        DEFAULT_ICON  = ""


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
    """Returns True when value looks like a shell command (not a bare app name)."""
    if not value:
        return False
    if '\\' in value:
        return True
    if '/' in value and not value.startswith('shell:'):
        return True
    parts = value.split()
    if len(parts) > 1 and parts[0].lower() in _CLI_PREFIXES:
        return True
    return False


def _parse_shell_and_cmd(value: str) -> tuple:
    """
    Checks whether the value starts with a known shell name.
    Returns (shell_override, command):
      - shell_override is the shell string if found, else None (→ use DEFAULT_SHELL)
      - command is the remainder of the value (or the full value if no shell prefix)
    """
    parts = value.split(None, 1)
    if parts and parts[0].lower() in _KNOWN_SHELLS:
        shell_override = parts[0].lower()
        cmd            = parts[1] if len(parts) > 1 else ""
        return shell_override, cmd
    return None, value


def _parse_cwd(parts: list) -> str | None:
    """
    Given a parsed command (list of tokens), returns the directory of the first
    .py argument if it exists on disk — used as the working directory so that
    scripts with relative imports/file paths work correctly.
    """
    for part in parts[1:]:
        p = part.strip('"').strip("'")
        if p.lower().endswith(".py") and os.path.isfile(p):
            return os.path.dirname(os.path.abspath(p))
    return None


def _launch_shell_command(cmd: str, shell_override: str | None = None) -> None:
    """
    Executes cmd via the configured default shell (or shell_override if provided).
    shell_override comes from a per-entry prefix in favorites.data, e.g.:
        btop=cmd btop
    Uses conhost.exe as the console host for cmd to bypass Windows Terminal,
    which would otherwise intercept CREATE_NEW_CONSOLE and open a PS7 tab.
    For Python scripts the CWD is automatically set to the script's directory.
    """
    shell = shell_override if shell_override else DEFAULT_SHELL.lower()

    cwd   = None
    parts = []
    exe   = ""
    try:
        parts = shlex.split(cmd, posix=False)
        exe   = os.path.splitext(parts[0].lower())[0] if parts else ""
        if exe in _PYTHON_EXECUTABLES:
            cwd = _parse_cwd(parts)
    except Exception:
        pass

    env = _clean_env()

    # Strategy:
    # - cmd  → conhost.exe (bypasses Windows Terminal which would otherwise open
    #           its default PS7 profile for cmd.exe on some WT configurations)
    # - pwsh/powershell/other → CREATE_NEW_CONSOLE directly: Windows Terminal
    #           recognises pwsh.exe and opens the correct PS7/PS5 profile.
    #
    # Pass commands as STRING to CreateProcess (not list) to avoid list2cmdline
    # adding extra quotes around tokens that already contain quoted paths.
    CREATE_NEW_CONSOLE = 0x00000010
    try:
        if shell == "cmd":
            subprocess.Popen(f'conhost.exe -- cmd.exe /k {cmd}',
                             cwd=cwd, env=env)
        elif shell in ("pwsh", "pwsh.exe"):
            subprocess.Popen(
                f'pwsh.exe -NoProfile -NoExit -Command {cmd}',
                creationflags=CREATE_NEW_CONSOLE, cwd=cwd, env=env)
        elif shell in ("powershell", "powershell.exe"):
            subprocess.Popen(
                f'powershell.exe -NoProfile -NoExit -Command {cmd}',
                creationflags=CREATE_NEW_CONSOLE, cwd=cwd, env=env)
        else:
            subprocess.Popen(
                f'{shell} -NoExit -Command {cmd}',
                creationflags=CREATE_NEW_CONSOLE, cwd=cwd, env=env)
    except FileNotFoundError:
        _eprint("Shell Plugin: shell not found, falling back to cmd.")
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
    # 1. User-defined custom icon (from default_shell.json)
    if DEFAULT_ICON and os.path.exists(DEFAULT_ICON):
        return {"icon_type": "file", "exe_path": DEFAULT_ICON}
    # 2. Bundled shell.svg
    bundled = _get_bundled_icon_path()
    if os.path.exists(bundled):
        return {"icon_path": bundled}
    # 3. Fallback to themed shell SVG icon
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

def on_search(text: str) -> list:
    query       = text.strip()
    query_lower = query.lower()

    # Empty query ("shell" typed alone) → list all favorites
    if not query:
        results = [_build_favorite_entry(k, 80.0) for k in list(FAVORITES.keys())[:14]]
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:15]

    results = []

    # ── 1. Favorites (fuzzy search over favorites.data keys) ────────────
    results.extend(_search_favorites(query_lower))

    # ── 2. Direct shell command (raw text input) ─────────────────────────
    # Supports inline shell prefix: "cmd btop" → use cmd
    if _is_shell_command(query):
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

    return deduped[:15]
