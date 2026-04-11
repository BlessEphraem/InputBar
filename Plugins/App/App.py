import os
import json
import subprocess
import winreg
from rapidfuzz import process, fuzz

try:
    import win32com.client
    _HAS_WIN32COM = True
except ImportError:
    _HAS_WIN32COM = False

MAX_TOTAL_ITEMS = 200
apps_index = []
ALIASES    = {}


def _generate_acronym(name: str) -> str:
    """Returns the acronym of a name (first letter of each word).
    Example: 'Yet Another Status Bar' → 'yasb'
    """
    return ''.join(w[0] for w in name.split() if w).lower()


def load_aliases():
    """Loads aliases from aliases.data if it exists (optional)."""
    global ALIASES
    ALIASES.clear()

    current_dir  = os.path.dirname(os.path.abspath(__file__))
    aliases_file = os.path.join(current_dir, "aliases.data")

    if os.path.exists(aliases_file):
        try:
            with open(aliases_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        ALIASES[key.strip().lower()] = value.strip().lower()
        except Exception as e:
            print(f"App Plugin: Unable to load aliases.data ({e})")


def resolve_lnk(lnk_path: str) -> str | None:
    """Resolves a .lnk shortcut to the real target exe path."""
    if not _HAS_WIN32COM or not lnk_path.endswith(".lnk"):
        return None
    try:
        shell    = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(lnk_path)
        target   = shortcut.Targetpath
        return target if target and os.path.exists(target) else None
    except Exception:
        return None


def _scan_registry(seen_names: set) -> list:
    """Scans the Windows registry for installed applications."""
    results   = []
    reg_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]

    for hive, reg_path in reg_paths:
        try:
            with winreg.OpenKey(hive, reg_path) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            # Skip system components and updates
                            try:
                                winreg.QueryValueEx(subkey, "ParentKeyName")
                                continue
                            except FileNotFoundError:
                                pass
                            try:
                                if winreg.QueryValueEx(subkey, "SystemComponent")[0] == 1:
                                    continue
                            except FileNotFoundError:
                                pass

                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            except FileNotFoundError:
                                continue

                            if not name or not name.strip():
                                continue
                            if name.lower() in seen_names:
                                continue

                            # Try to get the exe path via DisplayIcon
                            exe_path = None
                            try:
                                icon_val   = winreg.QueryValueEx(subkey, "DisplayIcon")[0]
                                icon_clean = icon_val.split(",")[0].strip().strip('"').strip("'")
                                if icon_clean.lower().endswith(".exe") and os.path.exists(icon_clean):
                                    exe_path = icon_clean
                            except FileNotFoundError:
                                pass

                            seen_names.add(name.lower())
                            results.append({
                                "name":     name.strip(),
                                "path":     exe_path or "",
                                "exe_path": exe_path,
                                "acronym":  _generate_acronym(name.strip()),
                            })
                    except Exception:
                        continue
        except Exception:
            continue

    return results


def build_index():
    """Indexes applications at module startup."""
    global apps_index
    apps_index.clear()
    seen_names = set()

    lnk_paths = [
        # Classic Start Menu
        os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("AppData", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
        # Desktop
        os.path.join(os.environ.get("Public", "C:\\Users\\Public"), "Desktop"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        # User-installed apps (Zen, Discord, Spotify, VS Code user…)
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
        # Pinned taskbar
        os.path.join(os.environ.get("AppData", ""), "Microsoft", "Internet Explorer", "Quick Launch", "User Pinned", "TaskBar"),
    ]

    # --- 1. SCAN CLASSIC SHORTCUTS (.lnk) ---
    for path in lnk_paths:
        if not os.path.exists(path):
            continue
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".lnk"):
                    app_name   = file[:-4]
                    name_lower = app_name.lower()
                    if name_lower in seen_names:
                        continue
                    seen_names.add(name_lower)
                    full_path = os.path.join(root, file)
                    apps_index.append({
                        "name":     app_name,
                        "path":     full_path,
                        "exe_path": None,  # lazy resolution in sub-menu
                        "acronym":  _generate_acronym(app_name),
                    })

    # --- 2. SCAN UWP APPS (MICROSOFT STORE) ---
    try:
        cmd = 'powershell -NoProfile -Command "$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8; Get-StartApps | Select-Object Name, AppID | ConvertTo-Json"'
        CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
        result = subprocess.check_output(cmd, shell=False, text=True, encoding="utf-8", creationflags=CREATE_NO_WINDOW)

        if result:
            store_apps = json.loads(result)
            if isinstance(store_apps, dict):
                store_apps = [store_apps]

            for app in store_apps:
                name  = app.get("Name")
                appid = app.get("AppID")
                if name and appid and name.lower() not in seen_names:
                    seen_names.add(name.lower())
                    apps_index.append({
                        "name":     name,
                        "path":     f"explorer.exe shell:appsFolder\\{appid}",
                        "exe_path": None,
                        "acronym":  _generate_acronym(name),
                    })
    except Exception as e:
        print(f"App Plugin: Error indexing UWP apps ({e})")

    # --- 3. SCAN WINDOWS REGISTRY ---
    try:
        reg_entries = _scan_registry(seen_names)
        apps_index.extend(reg_entries)
    except Exception as e:
        print(f"App Plugin: Error scanning registry ({e})")


# Initialisation
load_aliases()
build_index()


def _compute_score(query: str, name: str, wratio_score: float) -> float:
    """Computes the final score by combining WRatio, partial_ratio, and prefix boost."""
    name_lower  = name.lower()
    query_lower = query.lower()

    base = wratio_score

    # Boost partial_ratio for short queries (≤6 chars): "zen" finds "Zen Browser"
    if len(query_lower) <= 6:
        p    = fuzz.partial_ratio(query_lower, name_lower)
        base = max(base, p * 0.92)

    # Prefix boost: name starts with the query
    if name_lower.startswith(query_lower):
        base = max(base, 90.0)

    # Exact match
    if name_lower == query_lower:
        base = 100.0

    return base


def on_search(text):
    query       = text.strip()
    query_lower = query.lower()

    if not query:
        return []

    # Index reload command
    if query_lower in ("app rebuild", "app reload", "rebuild apps", "reload apps"):
        def _rebuild():
            build_index()
        return [{
            "name":      "🔄 App: Reload application index",
            "score":     2000,
            "action":    _rebuild,
            "icon_type": "settings",
        }]

    search_term = ALIASES.get(query_lower, query_lower)
    choices     = [app["name"] for app in apps_index]

    results      = []
    seen_indices = set()

    # --- PASS 1: exact acronym match (e.g. "yasb" → "Yet Another Status Bar") ---
    for i, app in enumerate(apps_index):
        if app.get("acronym") == search_term:
            seen_indices.add(i)
            results.append({
                "name":      app["name"],
                "score":     97.0,
                "action":    app["path"],
                "icon_type": "file",
                "item_type": "app",
                "exe_path":  app.get("exe_path"),
            })

    # --- PASS 2: exact substring in name (e.g. "code" in "VS Code") ---
    for i, app in enumerate(apps_index):
        if i in seen_indices:
            continue
        if len(search_term) >= 2 and search_term in app["name"].lower():
            seen_indices.add(i)
            results.append({
                "name":      app["name"],
                "score":     92.0,
                "action":    app["path"],
                "icon_type": "file",
                "item_type": "app",
                "exe_path":  app.get("exe_path"),
            })

    # --- PASS 3: fuzzy WRatio ---
    matches = process.extract(search_term, choices, scorer=fuzz.WRatio, limit=20)

    for name, score, index in matches:
        if index in seen_indices:
            continue
        seen_indices.add(index)

        final_score = _compute_score(search_term, name, score)

        if query_lower in ALIASES and score > 70:
            final_score = 100.0

        if final_score > 45:
            app = apps_index[index]
            results.append({
                "name":      name,
                "score":     final_score,
                "action":    app["path"],
                "icon_type": "file",
                "item_type": "app",
                "exe_path":  app.get("exe_path"),
            })

    # --- PASS 4: partial_ratio for short queries ---
    if len(search_term) <= 6:
        partial_matches = process.extract(search_term, choices, scorer=fuzz.partial_ratio, limit=15)
        for name, score, index in partial_matches:
            if index in seen_indices:
                continue
            if score < 70:
                continue
            seen_indices.add(index)
            app = apps_index[index]
            results.append({
                "name":      name,
                "score":     score * 0.92,
                "action":    app["path"],
                "icon_type": "file",
                "item_type": "app",
                "exe_path":  app.get("exe_path"),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:15]
