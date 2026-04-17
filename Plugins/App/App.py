import os
import re
import json
import subprocess
import threading
import winreg
from rapidfuzz import process, fuzz

try:
    import win32com.client
    _HAS_WIN32COM = True
except ImportError:
    _HAS_WIN32COM = False

from Core.Logging import eprint as _eprint
from Core.Paths import PLUGINS_DATA_DIR as _PLUGINS_DATA_DIR

_APP_DATA_DIR = os.path.join(_PLUGINS_DATA_DIR, "App")

_CREATE_NO_WINDOW = 0x08000000

apps_index    = []
choices_index = []
ALIASES       = {}

# Extensions that indicate a registry entry is a file/artifact, not an app
_JUNK_EXTS = {".txt", ".pdf", ".doc", ".docx", ".rtf", ".html", ".htm",
              ".chm", ".ini", ".log", ".nfo", ".url", ".xml"}

# Shortcut name filters: auxiliary / non-app shortcuts to exclude from the index.
# "TreeSize Free Help"    → last word "help"      → excluded
# "Uninstall MyApp"       → first word "uninstall" → excluded
# "MyApp Uninstall"       → last word "uninstall"  → excluded
_SKIP_LAST_WORDS  = frozenset({
    "help", "hilfe", "uninstall", "readme", "manual", "support", "website",
    "changelog", "documentation",
})
_SKIP_FIRST_WORDS = frozenset({"uninstall", "deinstall", "remove"})


def _is_aux_shortcut(name: str) -> bool:
    """Return True if *name* looks like a Help/Uninstall/ReadMe auxiliary shortcut."""
    words = name.lower().split()
    if not words:
        return False
    return words[-1] in _SKIP_LAST_WORDS or words[0] in _SKIP_FIRST_WORDS


_GUID_APPID_RE = re.compile(r'^\{[0-9a-fA-F\-]+\}\\(.+)$')
_DRIVE_APPID_RE = re.compile(r'^[A-Za-z]:\\')


def _resolve_appid(appid: str) -> tuple:
    """
    Translates a Get-StartApps AppID into (launch_path, exe_path, icon_type).

    - Real UWP  ('!' in AppID)           -> shell:appsFolder\\{appid}, None, "app"
    - GUID-based ('{GUID}\\\\app.exe')   -> shell:appsFolder\\{appid},
                                            resolved System32/SysWOW64 path or None,
                                            "file" / "app"
    - Full-path  ('C:\\\\...\\\\app.exe') -> exe path used directly, "file"
    - Anything else                       -> (None, None, None) -> skip
    """
    if "!" in appid:
        return f"shell:appsFolder\\{appid}", None, "app"

    m = _GUID_APPID_RE.match(appid)
    if m:
        rel = m.group(1)                              # e.g. "dfrgui.exe"
        if not rel.lower().endswith(".exe"):
            return None, None, None                   # skip non-app files (docs, txt, etc.)
        sys_root = os.environ.get("SystemRoot", r"C:\Windows")
        for folder in (
            os.path.join(sys_root, "System32"),
            os.path.join(sys_root, "SysWOW64"),
            sys_root,
        ):
            candidate = os.path.join(folder, rel)
            if os.path.exists(candidate):
                return f"shell:appsFolder\\{appid}", candidate, "file"
        return f"shell:appsFolder\\{appid}", None, "app"

    if _DRIVE_APPID_RE.match(appid) and appid.lower().endswith(".exe") and os.path.exists(appid):
        return appid, appid, "file"

    return None, None, None   # unrecognised format — skip


def _generate_acronym(name: str) -> str:
    """Returns the acronym of a name (first letter of each word).
    Example: 'Yet Another Status Bar' → 'yasb'
    """
    return ''.join(w[0] for w in name.split() if w).lower()


def _normalize_for_dedup(name: str) -> str:
    """
    Strip common version patterns so 'App version 1.2' and 'App' are
    treated as the same entry for deduplication purposes.
    """
    n = re.sub(r'\s+version\s+[\w\d\.\-]+', '', name, flags=re.IGNORECASE)
    n = re.sub(r'\s+v?\d+[\.\d]+\S*$', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s*\(v?\d[\d\.]+[^\)]*\)', '', n, flags=re.IGNORECASE)
    return n.strip().lower()


def load_aliases():
    """Loads aliases from aliases.data if it exists (optional)."""
    global ALIASES
    ALIASES.clear()

    aliases_file = os.path.join(_APP_DATA_DIR, "aliases.data")

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
            _eprint(f"App Plugin: Unable to load aliases.data ({e})")



def _scan_registry(seen_names: set, seen_normalized: set) -> list:
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

                            # Must have a DisplayName
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            except FileNotFoundError:
                                continue

                            if not name or not name.strip():
                                continue

                            # Must have an UninstallString — filters out file
                            # artifacts left behind by installers (e.g. License.txt)
                            try:
                                winreg.QueryValueEx(subkey, "UninstallString")
                            except FileNotFoundError:
                                continue

                            # Skip entries whose name ends with a known file extension
                            name_stripped = name.strip()
                            if any(name_stripped.lower().endswith(ext) for ext in _JUNK_EXTS):
                                continue

                            # Skip auxiliary registry entries: "App Help", "Uninstall App", etc.
                            if _is_aux_shortcut(name_stripped):
                                continue

                            # Exact-name dedup
                            if name_stripped.lower() in seen_names:
                                continue

                            # Normalized-name dedup (catches "App version 1.2" when "App" exists)
                            norm = _normalize_for_dedup(name_stripped)
                            if norm in seen_normalized:
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

                            # Skip entries with no launchable exe — they can't be opened
                            # (path would be "" → os.startfile("") silently fails)
                            if not exe_path:
                                continue

                            seen_names.add(name_stripped.lower())
                            seen_normalized.add(norm)
                            results.append({
                                "name":      name_stripped,
                                "path":      exe_path,
                                "exe_path":  exe_path,
                                "icon_type": "file",
                                "acronym":   _generate_acronym(name_stripped),
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
    seen_names      = set()   # exact lowercased names
    seen_normalized = set()   # version-stripped names for dedup

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
    # Create the COM shell object once — reused for every .lnk file.
    _wsh = None
    if _HAS_WIN32COM:
        try:
            _wsh = win32com.client.Dispatch("WScript.Shell")
        except Exception:
            pass

    for path in lnk_paths:
        if not os.path.exists(path):
            continue
        for root, dirs, files in os.walk(path):
            for file in files:
                if not file.endswith(".lnk"):
                    continue
                app_name = file[:-4]

                # Filename-based filter: catches "license.txt.lnk" → "license.txt"
                if any(app_name.lower().endswith(ext) for ext in _JUNK_EXTS):
                    continue

                # Name-based filter: "TreeSize Free Help", "Uninstall MyApp", etc.
                if _is_aux_shortcut(app_name):
                    continue

                name_lower = app_name.lower()
                if name_lower in seen_names:
                    continue
                norm = _normalize_for_dedup(app_name)
                if norm in seen_normalized:
                    continue

                full_path    = os.path.join(root, file)
                exe_target   = None
                direct_icon  = None
                _com_success = False

                if _wsh:
                    try:
                        shortcut     = _wsh.CreateShortCut(full_path)
                        target       = shortcut.Targetpath.strip('"').strip()
                        icon_raw     = shortcut.IconLocation or ""
                        icon_file    = icon_raw.split(",")[0].strip('"').strip()
                        _com_success = True

                        # Skip if target is a known document/artifact extension
                        if target and any(target.lower().endswith(ext) for ext in _JUNK_EXTS):
                            continue

                        # Skip shortcuts whose target is not an exe or a folder.
                        # Checked regardless of whether the target file currently exists —
                        # a stale .lnk pointing to a deleted .chm is still not an app.
                        if target and not target.lower().endswith(".exe") and not os.path.isdir(target):
                            continue

                        # Skip if the icon location is itself a document
                        if icon_file and any(icon_file.lower().endswith(ext) for ext in _JUNK_EXTS):
                            continue

                        # Resolve icon source: only from the actual target exe or a .ico file.
                        # Do NOT fall back to the icon-location exe — that exe may be the main
                        # app of a Help/Readme shortcut (e.g. TreeSizeFree.exe used as Help icon),
                        # which would make the entry look launchable when it is not.
                        if target.lower().endswith(".exe") and os.path.exists(target):
                            exe_target = target
                        elif icon_file.lower().endswith(".ico") and os.path.exists(icon_file):
                            direct_icon = icon_file

                        # Reject auxiliary executables even when they are real .exe files:
                        # unins000.exe, TreeSizeFreeHelp.exe, RemoveApp.exe, etc.
                        if exe_target:
                            _stem = os.path.splitext(os.path.basename(exe_target))[0].lower()
                            if any(kw in _stem for kw in {
                                "help", "uninstall", "unins", "readme", "remove",
                            }):
                                exe_target = None   # guard below will skip the entry
                    except Exception:
                        pass  # COM failed — unknown status

                # If pywin32 was available but we found no usable exe/icon, skip.
                # Covers: COM exception on a specific .lnk, empty-target UWP shortcuts
                # (indexed properly via Get-StartApps in Step 2), and Help/Readme shortcuts
                # whose icon source was a foreign .exe.
                if not exe_target and not direct_icon and _HAS_WIN32COM:
                    continue

                seen_names.add(name_lower)
                seen_normalized.add(norm)
                apps_index.append({
                    "name":      app_name,
                    "path":      full_path,
                    "exe_path":  exe_target,
                    "icon_path": direct_icon,
                    "icon_type": "file" if (exe_target or direct_icon) else "app",
                    "acronym":   _generate_acronym(app_name),
                })

    # --- 2. SCAN UWP APPS (MICROSOFT STORE) ---
    # Step A: get app list — fast query, never blocks indexing.
    store_apps: list = []
    try:
        cmd_list = (
            'powershell -NoProfile -Command "'
            '$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8;'
            'Get-StartApps | Select-Object Name, AppID | ConvertTo-Json"'
        )
        raw = subprocess.check_output(
            cmd_list, shell=False, text=True, encoding="utf-8",
            creationflags=_CREATE_NO_WINDOW, timeout=10,
        )
        parsed = json.loads(raw)
        store_apps = [parsed] if isinstance(parsed, dict) else parsed
    except Exception as e:
        _eprint(f"App Plugin: Error listing UWP apps ({e})")

    # Step C: add apps immediately (icons filled in by background thread).
    _appid_to_index: dict[str, int] = {}
    for app in store_apps:
        name  = app.get("Name")
        appid = app.get("AppID")
        if not name or not appid:
            continue
        # Get-StartApps returns everything in the Start Menu, including Help,
        # Uninstall, and ReadMe entries — filter them by name just like the lnk scan.
        if _is_aux_shortcut(name):
            continue
        if any(name.lower().endswith(ext) for ext in _JUNK_EXTS):
            continue
        launch_path, exe_path_val, icon_type_val = _resolve_appid(appid)
        if launch_path is None:
            continue                       # unrecognised format (steam://, https://, …)
        name_lower = name.lower()
        if name_lower in seen_names:
            continue
        norm = _normalize_for_dedup(name)
        if norm in seen_normalized:
            continue
        seen_names.add(name_lower)
        seen_normalized.add(norm)
        _appid_to_index[appid] = len(apps_index)
        apps_index.append({
            "name":      name,
            "path":      launch_path,
            "exe_path":  exe_path_val,
            "icon_path": None,
            "icon_type": icon_type_val,
            "acronym":   _generate_acronym(name),
        })

    # Step B: enrich with package icons in a background daemon thread.
    # $pkg.Logo is a relative path; Windows stores scaled variants like
    # Logo.scale-200.png. We pick the highest-resolution variant first.
    def _fetch_uwp_icons(appid_map: dict[str, int], create_flags: int) -> None:
        ps_icons = (
            '$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8;'
            'Get-StartApps | Where-Object { $_.AppID -like "*!*" } | ForEach-Object {'
            '  $pfn = $_.AppID.Split("!")[0];'
            '  $lastUs = $pfn.LastIndexOf("_");'
            '  $pkgName = if ($lastUs -ge 0) { $pfn.Substring(0, $lastUs) } else { $pfn };'
            '  $pkg = Get-AppxPackage -Name $pkgName -ErrorAction SilentlyContinue | Select-Object -First 1;'
            '  $icon = $null;'
            '  if ($pkg -and $pkg.InstallLocation) {'
            '    $manifest = Join-Path $pkg.InstallLocation "AppxManifest.xml";'
            '    if (Test-Path $manifest) {'
            '      $xml = [xml](Get-Content $manifest -ErrorAction SilentlyContinue);'
            '      $logo = $xml.Package.Properties.Logo;'
            '      if ($logo) {'
            '        $full = Join-Path $pkg.InstallLocation $logo;'
            '        $dir  = Split-Path $full -Parent;'
            '        $base = [IO.Path]::GetFileNameWithoutExtension($full);'
            '        $ext  = [IO.Path]::GetExtension($full);'
            '        $match = Get-ChildItem $dir -Filter "$base*$ext" -ErrorAction SilentlyContinue'
            '                 | Sort-Object Name -Descending | Select-Object -First 1;'
            '        if ($match) { $icon = $match.FullName }'
            '        elseif (Test-Path $full) { $icon = $full }'
            '      }'
            '    }'
            '  }'
            '  [PSCustomObject]@{ AppID=$_.AppID; IconPath=$icon }'
            '} | ConvertTo-Json'
        )
        try:
            raw_icons = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_icons],
                shell=False, text=True, encoding="utf-8",
                creationflags=create_flags, timeout=20,
            )
            parsed_icons = json.loads(raw_icons)
            if isinstance(parsed_icons, dict):
                parsed_icons = [parsed_icons]
            for entry in parsed_icons:
                appid = entry.get("AppID")
                icon  = entry.get("IconPath")
                if appid and icon and appid in appid_map:
                    idx = appid_map[appid]
                    apps_index[idx]["icon_path"] = icon
                    apps_index[idx]["icon_type"]  = "file"
        except Exception as e:
            _eprint(f"App Plugin: Could not fetch UWP icons ({e}) — apps will still be indexed")

    if _appid_to_index:
        threading.Thread(
            target=_fetch_uwp_icons,
            args=(_appid_to_index, _CREATE_NO_WINDOW),
            daemon=True,
        ).start()

    # --- 3. SCAN WINDOWS REGISTRY ---
    try:
        reg_entries = _scan_registry(seen_names, seen_normalized)
        apps_index.extend(reg_entries)
    except Exception as e:
        _eprint(f"App Plugin: Error scanning registry ({e})")

    global choices_index
    choices_index.clear()
    for app in apps_index:
        action = app.get("path")
        is_launchable = False
        if action:
            if callable(action) or action.startswith("shell:appsFolder\\"):
                is_launchable = True
            elif _HAS_WIN32COM and app.get("icon_type") == "app":
                is_launchable = False
            else:
                is_launchable = os.path.exists(action)
        app["is_launchable"] = is_launchable
        choices_index.append(app["name"])

    launchable_count = sum(1 for a in apps_index if a.get("is_launchable"))
    _eprint(f"[DEBUG] build_index: total={len(apps_index)}, launchable={launchable_count}, choices={len(choices_index)}")


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

    search_term = ALIASES.get(query_lower, query_lower)

    results      = []
    seen_indices = set()

    # --- PASS 1 & 2: exact acronym match or substring match ---
    for i, app in enumerate(apps_index):
        if not app.get("is_launchable", False):
            continue
            
        score = 0.0
        if app.get("acronym") == search_term:
            score = 97.0
        elif len(search_term) >= 2 and search_term in app["name"].lower():
            score = 92.0
            
        if score > 0.0:
            seen_indices.add(i)
            results.append({
                "name":      app["name"],
                "score":     score,
                "action":    app["path"],
                "icon_type": app.get("icon_type", "file"),
                "icon_path": app.get("icon_path"),
                "item_type": "app",
                "exe_path":  app.get("exe_path"),
            })

    # --- PASS 3: fuzzy WRatio ---
    matches = process.extract(search_term, choices_index, scorer=fuzz.WRatio, limit=20)

    for name, score, index in matches:
        if index in seen_indices:
            continue
            
        app = apps_index[index]
        if not app.get("is_launchable", False):
            continue

        seen_indices.add(index)

        final_score = _compute_score(search_term, name, score)

        if query_lower in ALIASES and score > 70:
            final_score = 100.0

        if final_score > 45:
            results.append({
                "name":      name,
                "score":     final_score,
                "action":    app["path"],
                "icon_type": app.get("icon_type", "file"),
                "icon_path": app.get("icon_path"),
                "item_type": "app",
                "exe_path":  app.get("exe_path"),
            })

    # --- PASS 4: partial_ratio for short queries ---
    if len(search_term) <= 6:
        partial_matches = process.extract(search_term, choices_index, scorer=fuzz.partial_ratio, limit=15)
        for name, score, index in partial_matches:
            if index in seen_indices:
                continue
            if score < 70:
                continue
                
            app = apps_index[index]
            if not app.get("is_launchable", False):
                continue
                
            seen_indices.add(index)
            results.append({
                "name":      name,
                "score":     score * 0.92,
                "action":    app["path"],
                "icon_type": app.get("icon_type", "file"),
                "icon_path": app.get("icon_path"),
                "item_type": "app",
                "exe_path":  app.get("exe_path"),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
