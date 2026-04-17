"""
Everything Plugin for InputBar
Searches files and folders using the Everything search engine (voidtools.com).

Requirements:
  - Everything must be installed on the user's computer.
  - The plugin starts Everything silently if it is not already running.
  - Uses the Everything SDK DLLs (Everything32.dll / Everything64.dll).

Configuration files (in {PLUGINS_DATA_DIR}/Everything/):
  - EverythingPath.json : {"EverythingPath": "C:\\...\\Everything.exe"}
  - extensions.data     : file extensions that auto-trigger the plugin
  - favorites.data      : named shortcuts to files/folders (key=path)

Keywords:
  - "everything" / "f" (strict) : searches directly for the typed query
  - "*" (global)                : triggers only when detection rules match
    Detection rules: query contains \\ or / , OR ends with a known extension.
"""

import os
import json
import ctypes
import ctypes.wintypes as wt
import subprocess
import threading
import winreg
import urllib.parse
from rapidfuzz import process, fuzz

from Core.Logging import eprint as _eprint, dprint
from Core.Paths import PLUGINS_DATA_DIR as _PLUGINS_DATA_DIR

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# ─────────────────────────────────────────────────────────────────────────────
#  Paths
# ─────────────────────────────────────────────────────────────────────────────

_DATA_DIR             = os.path.join(_PLUGINS_DATA_DIR, "Everything")
_EVERYTHING_PATH_FILE = os.path.join(_DATA_DIR, "EverythingPath.json")
_EXTENSIONS_FILE      = os.path.join(_DATA_DIR, "extensions.data")
_FAVORITES_FILE       = os.path.join(_DATA_DIR, "favorites.data")

# ─────────────────────────────────────────────────────────────────────────────
#  Module-level state
# ─────────────────────────────────────────────────────────────────────────────

_EVERYTHING_EXE:   str | None = None
_EXTENSIONS:       set[str]   = set()
_FAVORITES:        dict       = {}
_query_fail_count: int        = 0
_QUERY_FAIL_THRESHOLD          = 3

# ─────────────────────────────────────────────────────────────────────────────
#  DLL SDK Setup
# ─────────────────────────────────────────────────────────────────────────────

_IS_64BIT = ctypes.sizeof(ctypes.c_void_p) == 8
_DLL_NAME = "Everything64.dll" if _IS_64BIT else "Everything32.dll"
_DLL_PATH = os.path.join(os.path.dirname(__file__), _DLL_NAME)

_ev_dll = None
if os.path.exists(_DLL_PATH):
    try:
        _ev_dll = ctypes.WinDLL(_DLL_PATH)
        # Define prototypes
        _ev_dll.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
        _ev_dll.Everything_SetMax.argtypes    = [ctypes.c_uint32]
        _ev_dll.Everything_SetSort.argtypes   = [ctypes.c_uint32]
        _ev_dll.Everything_QueryW.argtypes     = [ctypes.c_bool]
        _ev_dll.Everything_QueryW.restype      = ctypes.c_bool
        _ev_dll.Everything_GetNumResults.restype = ctypes.c_int
        _ev_dll.Everything_GetResultFullPathNameW.argtypes = [ctypes.c_int, ctypes.c_wchar_p, ctypes.c_int]
    except Exception as e:
        _eprint(f"Everything Plugin: Error loading {_DLL_NAME}: {e}")
else:
    _eprint(f"Everything Plugin: SDK DLL not found at {_DLL_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
#  Query Everything via SDK DLL
# ─────────────────────────────────────────────────────────────────────────────

def _build_everything_query(query: str) -> str:
    """
    Translate a user query into optimal Everything search syntax.

    Rules (applied in order, first match wins):
      - Contains \\ or /          → return unchanged (path expression)
      - Contains spaces           → return unchanged (multi-word / composite)
      - Bare extension (.png/png) → "ext:png"
      - stem.ext  where .ext is a known extension
                                  → "ext:ext stem"  (e.g. "image.png" → "ext:png image")
      - Anything else             → return unchanged
    """
    q = query.strip()
    if not q:
        return q

    # Path-like: let Everything interpret it as-is
    if "\\" in q or "/" in q:
        return q

    # Multi-word / already-composed Everything syntax → unchanged
    if " " in q:
        return q

    lower = q.lower()

    # Bare extension: ".png" or "png"
    bare = lower.lstrip(".")
    if bare and ("." + bare) in _EXTENSIONS and ("." not in q or q == "." + bare):
        return "ext:" + bare

    # "stem.ext" where the extension is known
    if "." in q:
        stem, ext = os.path.splitext(q)      # e.g. ("image", ".png")
        ext_lower = ext.lower()
        if stem and ext_lower in _EXTENSIONS:
            return f"ext:{ext_lower.lstrip('.')} {stem}"

    return q


def _build_scoped_query(folder_path: str, subquery: str) -> str:
    """
    Build an Everything query scoped to *folder_path* with an optional sub-filter.

    Examples:
      ("Z:\\Wall", "")           → 'parent:"Z:\\Wall"'
      ("Z:\\Wall", ".png")       → 'parent:"Z:\\Wall" ext:png'
      ("Z:\\Wall", "image.png")  → 'parent:"Z:\\Wall" ext:png image'
      ("Z:\\Wall", "project")    → 'parent:"Z:\\Wall" project'
    """
    folder = folder_path.rstrip("\\/").strip()
    base   = f'parent:"{folder}"'

    sub = (subquery or "").strip()
    if not sub:
        return base

    translated = _build_everything_query(sub)
    return f"{base} {translated}"


def _query_everything(query: str, max_results: int = 20):
    """
    Send a query to Everything via the SDK DLL.
    Yields result dicts one by one.
    Auto-restarts Everything.exe if the DLL consistently fails.
    """
    global _query_fail_count

    if not _ev_dll:
        return

    search_query = _build_everything_query(query)

    try:
        _ev_dll.Everything_SetSearchW(search_query)
        _ev_dll.Everything_SetMax(max_results)
        # 14 = EVERYTHING_IPC_SORT_DATE_MODIFIED_DESCENDING
        _ev_dll.Everything_SetSort(14)

        if not _ev_dll.Everything_QueryW(True):
            _query_fail_count += 1
            if _query_fail_count >= _QUERY_FAIL_THRESHOLD and _EVERYTHING_EXE:
                if not _is_everything_running():
                    _eprint("Everything Plugin: Everything.exe not running — restarting...")
                    _start_everything(_EVERYTHING_EXE)
                    _query_fail_count = 0
            return

        _query_fail_count = 0
        num = _ev_dll.Everything_GetNumResults()
        buf = ctypes.create_unicode_buffer(32768)

        for i in range(num):
            _ev_dll.Everything_GetResultFullPathNameW(i, buf, 32768)
            full_path = buf.value
            if full_path:
                yield {
                    "name":      os.path.basename(full_path),
                    "subtitle":  os.path.dirname(full_path),
                    "score":     85 - i,
                    "action":    full_path,
                    "icon_type": "file",
                    "exe_path":  full_path,
                    "item_type": "file",
                }
    except Exception as e:
        _eprint(f"Everything Plugin: DLL Query error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
#  Default data files
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_EXTENSIONS = """\
# Everything Plugin — Extensions
# Extensions listed here auto-trigger a file search when typed in InputBar.
# One extension per line. Lines starting with '#' are ignored.

# Documents
.pdf
.doc
.docx
.txt
.rtf
.odt
.md
.csv
.xls
.xlsx
.ppt
.pptx

# Images
.png
.jpg
.jpeg
.gif
.svg
.webp
.bmp
.ico
.tiff

# Videos
.mp4
.mkv
.avi
.mov
.wmv
.webm
.flv

# Audio
.mp3
.wav
.flac
.ogg
.m4a
.aac

# Archives
.zip
.rar
.7z
.tar
.gz
.iso

# Code & Web
.json
.xml
.html
.css
.js
.ts
.py
.java
.cpp
.c
.cs
.php
.sql
.yml
.yaml

# System & Scripts
.exe
.msi
.bat
.cmd
.ps1
.sh
.ini
.cfg
.dll
.lnk
"""

_DEFAULT_FAVORITES = """\
# Everything Plugin — Favorites
# Named shortcuts to files or folders.
#
# Format:  key=file or folder path
#   key   — the name you type in InputBar (case-insensitive, fuzzy)
#   path  — the file or folder to open
#
# Examples:
# Desktop=C:\\Users\\YourName\\Desktop
# Downloads=C:\\Users\\YourName\\Downloads
# Projects=D:\\Dev\\Projects
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Data file helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_default_files() -> None:
    os.makedirs(_DATA_DIR, exist_ok=True)
    if not os.path.exists(_EXTENSIONS_FILE):
        try:
            with open(_EXTENSIONS_FILE, "w", encoding="utf-8") as f:
                f.write(_DEFAULT_EXTENSIONS)
        except Exception as e:
            _eprint(f"Everything Plugin: Could not create extensions.data ({e})")

    if not os.path.exists(_FAVORITES_FILE):
        try:
            with open(_FAVORITES_FILE, "w", encoding="utf-8") as f:
                f.write(_DEFAULT_FAVORITES)
        except Exception as e:
            _eprint(f"Everything Plugin: Could not create favorites.data ({e})")


def _load_extensions() -> None:
    global _EXTENSIONS
    _EXTENSIONS = set()
    if not os.path.exists(_EXTENSIONS_FILE):
        return
    try:
        with open(_EXTENSIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                ext = line.lower()
                if not ext.startswith("."):
                    ext = "." + ext
                _EXTENSIONS.add(ext)
    except Exception as e:
        _eprint(f"Everything Plugin: Could not load extensions.data ({e})")


def _load_favorites() -> None:
    global _FAVORITES
    _FAVORITES = {}
    if not os.path.exists(_FAVORITES_FILE):
        return
    try:
        with open(_FAVORITES_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, path = line.split("=", 1)
                    key  = key.strip().lower()
                    path = path.strip()
                    if key:
                        _FAVORITES[key] = path
    except Exception as e:
        _eprint(f"Everything Plugin: Could not load favorites.data ({e})")


def _load_everything_path() -> str | None:
    if not os.path.exists(_EVERYTHING_PATH_FILE):
        return None
    try:
        with open(_EVERYTHING_PATH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        path = data.get("EverythingPath", "").strip()
        if path and os.path.isfile(path):
            return path
    except Exception as e:
        _eprint(f"Everything Plugin: Could not read EverythingPath.json ({e})")
    return None


def _save_everything_path(path: str) -> None:
    try:
        with open(_EVERYTHING_PATH_FILE, "w", encoding="utf-8") as f:
            json.dump({"EverythingPath": path}, f, indent=4)
    except Exception as e:
        _eprint(f"Everything Plugin: Could not write EverythingPath.json ({e})")


# ─────────────────────────────────────────────────────────────────────────────
#  Everything.exe discovery
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_INSTALL_PATHS = [
    r"C:\Program Files\Everything\Everything.exe",
    r"C:\Program Files (x86)\Everything\Everything.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Everything\Everything.exe"),
    os.path.join(os.environ.get("USERPROFILE", ""), r"AppData\Local\Programs\Everything\Everything.exe"),
]

_REGISTRY_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Everything",             ""),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Everything", ""),
    (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Everything",             ""),
]


def _find_everything_exe() -> str | None:
    for hive, key_path, value_name in _REGISTRY_PATHS:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                val, _ = winreg.QueryValueEx(key, value_name)
                if isinstance(val, str):
                    candidate = val.strip()
                    if candidate.lower().endswith(".exe") and os.path.isfile(candidate):
                        return candidate
                    exe = os.path.join(candidate, "Everything.exe")
                    if os.path.isfile(exe):
                        return exe
        except Exception:
            continue

    for path in _DEFAULT_INSTALL_PATHS:
        if os.path.isfile(path):
            return path

    return None


# ─────────────────────────────────────────────────────────────────────────────
#  Toast notification (error when Everything not found)
# ─────────────────────────────────────────────────────────────────────────────

def _show_toast_error() -> None:
    folder_uri = "file:///" + urllib.parse.quote(
        _DATA_DIR.replace("\\", "/"), safe="/:"
    )
    title      = "InputBar \u2014 Everything Plugin"
    body       = (
        '"Everything" was not found on this computer.\n'
        "It will stay enabled but will not work.\n"
        "You can specify the executable yourself in the plugin config file."
    )
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace("'", "''")
    safe_body  = body.replace("&", "&amp;").replace("<", "&lt;").replace("'", "''")
    actions_xml = (
        f'<actions><action content="Open Config Folder"'
        f' activationType="protocol" arguments="{folder_uri}"/></actions>'
    )
    script = (
        "$appId = 'InputBar';"
        " $reg = \"HKCU:\\SOFTWARE\\Classes\\AppUserModelId\\$appId\";"
        " New-Item -Path $reg -Force | Out-Null;"
        " Set-ItemProperty -Path $reg -Name 'DisplayName' -Value 'InputBar';"
        " [void][Windows.UI.Notifications.ToastNotificationManager,"
        " Windows.UI.Notifications, ContentType=WindowsRuntime];"
        " [void][Windows.Data.Xml.Dom.XmlDocument,"
        " Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime];"
        " $xml = New-Object Windows.Data.Xml.Dom.XmlDocument;"
        f" $xml.LoadXml('<toast><visual><binding template=\"ToastGeneric\">"
        f"<text>{safe_title}</text>"
        f"<text>{safe_body}</text>"
        f"</binding></visual>{actions_xml}</toast>');"
        " $toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
        " [Windows.UI.Notifications.ToastNotificationManager]"
        "::CreateToastNotifier($appId).Show($toast)"
    )
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        _eprint(f"Everything Plugin: Could not show toast notification ({e})")


# ─────────────────────────────────────────────────────────────────────────────
#  Process helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_everything_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq Everything.exe", "/NH"],
            creationflags=_CREATE_NO_WINDOW,
            timeout=5,
        )
        return b"Everything.exe" in out
    except Exception:
        return False


def _start_everything(exe_path: str) -> None:
    CREATE_NO_WINDOW = 0x08000000
    try:
        subprocess.Popen([exe_path, "-startup"], creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        _eprint(f"Everything Plugin: Could not start Everything.exe ({e})")


# ─────────────────────────────────────────────────────────────────────────────
#  Startup sequence (daemon thread — does not block InputBar startup)
# ─────────────────────────────────────────────────────────────────────────────

def _startup() -> None:
    global _EVERYTHING_EXE

    # 1. Resolve Everything.exe path
    exe = _load_everything_path()
    if exe is None:
        exe = _find_everything_exe()
        if exe:
            _save_everything_path(exe)
            _eprint(f"Everything Plugin: Auto-detected at {exe}")

    if exe is None:
        _eprint("Everything Plugin: Everything.exe not found — plugin inactive")
        _show_toast_error()
        return

    _EVERYTHING_EXE = exe

    # 2. Start Everything silently if not already running
    if not _is_everything_running():
        dprint("Everything Plugin: launching Everything.exe...")
        _start_everything(exe)

    dprint(f"Everything Plugin: ready (DLL={_DLL_NAME})")


# ─────────────────────────────────────────────────────────────────────────────
#  Favorites search
# ─────────────────────────────────────────────────────────────────────────────

def _build_favorite_entry(key: str, score: float) -> dict:
    path = _FAVORITES[key]
    return {
        "name":      key,
        "subtitle":  path,
        "score":     score,
        "action":    path,
        "icon_type": "file",
        "exe_path":  path,
        "item_type": "file",
    }


def _search_favorites(query_lower: str) -> list:
    if not _FAVORITES:
        return []
    keys    = list(_FAVORITES.keys())
    results = []
    seen    = set()

    if query_lower in _FAVORITES:
        seen.add(query_lower)
        results.append(_build_favorite_entry(query_lower, 100.0))

    for key in keys:
        if key in seen: continue
        if key.startswith(query_lower):
            seen.add(key)
            results.append(_build_favorite_entry(key, 92.0))

    if len(query_lower) >= 2:
        for key in keys:
            if key in seen: continue
            if query_lower in key:
                seen.add(key)
                results.append(_build_favorite_entry(key, 85.0))

    if len(query_lower) >= 2:
        for key, score, _ in process.extract(
            query_lower, keys, scorer=fuzz.WRatio, limit=10
        ):
            if key in seen or score < 50: continue
            seen.add(key)
            results.append(_build_favorite_entry(key, score * 0.9))

    return results


# ─────────────────────────────────────────────────────────────────────────────
#  Module initialisation
# ─────────────────────────────────────────────────────────────────────────────

_ensure_default_files()
_load_extensions()
_load_favorites()

threading.Thread(target=_startup, daemon=True, name="Everything-Startup").start()

# ─────────────────────────────────────────────────────────────────────────────
#  on_search — plugin entry point
# ─────────────────────────────────────────────────────────────────────────────

def on_search(text: str, is_strict: bool = False):
    """
    Decision tree (each numbered step returns early if it fires):

    1. Empty query       → list all favorites
    2. Exact key match   → show favorite + scoped Everything search (with optional subquery)
    3. Path query        → folder contents (parent:) or raw path search — NO fuzzy favorites
    4. Fuzzy favorites   → non-path, non-exact-key queries; expand first folder hit
    5. Extension match   → global Everything search with ext: translation
    6. Strict mode       → raw Everything search with score boost
    """
    query       = text.strip()
    query_lower = query.lower()

    # ── Step 1: Empty query → list favorites ────────────────────────────────
    if not query:
        count = 0
        for k in _FAVORITES:
            yield _build_favorite_entry(k, 80.0)
            count += 1
            if count >= 14:
                break
        return

    # Detect path-like queries (backslash, forward-slash, or drive letter "C:")
    # NOTE: multi-word favorite keys are not supported; first token is used.
    is_path_query = (
        "\\" in query
        or "/" in query
        or (len(query) >= 2 and query[1] == ":")
    )

    # ── Step 2: Exact favorite key (first whitespace token) ─────────────────
    # "wallpapers .png" → key="wallpapers", subquery=".png"
    # "src"             → key="src",         subquery=""
    first_token = query.split(None, 1)[0].lower()
    subquery    = query[len(first_token):].lstrip()          # preserves original casing

    if first_token in _FAVORITES:
        fav_path = _FAVORITES[first_token]
        yield _build_favorite_entry(first_token, 100.0)
        if os.path.isdir(fav_path):
            scoped = _build_scoped_query(fav_path, subquery)
            yield from _query_everything(scoped, max_results=30)
        return

    # ── Step 3: Path query ───────────────────────────────────────────────────
    # Skip fuzzy favorites entirely — they produce false positives for paths.
    if is_path_query:
        clean = query.rstrip("\\/")
        try:
            is_dir = os.path.isdir(clean)
        except Exception:
            is_dir = False

        if is_dir:
            yield from _query_everything(f'parent:"{clean}"', max_results=30)
        else:
            yield from _query_everything(query, max_results=30)
        return

    # ── Step 4: Fuzzy favorites (non-path, non-exact-key) ───────────────────
    folder_to_expand: str | None = None
    for fav in _search_favorites(query_lower):
        yield fav
        if folder_to_expand is None:
            fav_path = fav.get("action", "")
            try:
                if os.path.isdir(fav_path):
                    folder_to_expand = fav_path
            except Exception:
                pass

    if folder_to_expand:
        yield from _query_everything(f'parent:"{folder_to_expand}"', max_results=20)

    # ── Step 5: Extension detection → global search ──────────────────────────
    if not is_strict:
        has_ext = any(query_lower.endswith(ext) for ext in _EXTENSIONS)
        if has_ext:
            seen_names: set[str] = set()
            for res in _query_everything(_build_everything_query(query), max_results=15):
                if res["name"] not in seen_names:
                    seen_names.add(res["name"])
                    yield res
            return

    # ── Step 6: Strict mode ("f …" / "everything …") ────────────────────────
    if is_strict:
        seen_names = set()
        for res in _query_everything(query, max_results=30):
            if res["name"] not in seen_names:
                seen_names.add(res["name"])
                res["score"] += 100
                yield res
