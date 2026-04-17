import os
import json
import sys
import importlib.util
from Core.Paths import PLUGINS_DIR, CORE_DIR, PLUGINS_FILE
from Core.Logging import dprint, eprint

loaded_plugins  = []
_plugins_cache  = None

# Plugins that should always respond to every query (global mode).
# Even if Plugins.json was generated before "calc" was in this set,
# the runtime check below injects "*" at load time.
_ALWAYS_GLOBAL = {"app", "shell", "system", "calc"}

# Extra keywords added alongside the base name when a plugin entry is first created.
_EXTRA_KEYWORDS: dict[str, list[str]] = {
    "everything": ["f"],
    "shell":      ["/"],
}


# ──────────────────────────────────────────────
#  Core module loader (no config file)
# ──────────────────────────────────────────────

def _load_core(folder):
    """Loads Core modules. Always enabled; keyword = module filename (lower-cased)."""
    if not os.path.exists(folder):
        return
    for root, _, filenames in os.walk(folder):
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            path        = os.path.join(root, filename)
            module_name = filename[:-3]
            try:
                spec   = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, "on_search"):
                    if not hasattr(module, "_keywords"):
                        module._keywords = [module_name.lower()]
                    loaded_plugins.append(module)
                    dprint(f"Core loaded: {module_name} (keyword: {module._keywords})")
            except Exception as e:
                eprint(f"Error loading core module {filename}: {e}")


# ──────────────────────────────────────────────
#  Plugin loader (Plugins.json config)
# ──────────────────────────────────────────────

def _sync_plugins_config(current_files):
    """
    Reads Plugins.json, migrates legacy format, adds new plugin entries,
    then writes it back. Returns the up-to-date config dict.
    """
    data = {}
    if os.path.exists(PLUGINS_FILE):
        try:
            with open(PLUGINS_FILE, "r") as f:
                data = json.load(f)
        except Exception:
            data = {}

    new_data = {}

    # Migrate old format (bool) and keep only files still present on disk
    for name, conf in data.items():
        if name not in current_files:
            continue
        if isinstance(conf, bool):
            base_name = os.path.basename(name)[:-3].lower()
            kws = [base_name] + _EXTRA_KEYWORDS.get(base_name, [])
            if base_name in _ALWAYS_GLOBAL:
                kws.append("*")
            new_data[name] = {"toggle": conf, "keyword": kws, "limit": 15}
        else:
            if "limit" not in conf:
                conf["limit"] = 15
            new_data[name] = conf

    # Add new plugins not yet tracked
    for file in current_files:
        if file not in new_data:
            base_name = os.path.basename(file)[:-3].lower()
            kws = [base_name] + _EXTRA_KEYWORDS.get(base_name, [])
            if base_name in _ALWAYS_GLOBAL:
                kws.append("*")
            new_data[file] = {"toggle": True, "keyword": kws, "limit": 15}

    try:
        with open(PLUGINS_FILE, "w") as f:
            json.dump(new_data, f, indent=4)
    except Exception as e:
        eprint(f"Error writing Plugins.json: {e}")

    return new_data


def _load_plugins(folder):
    """Loads user plugins according to Plugins.json (toggle + keywords)."""
    if not os.path.exists(folder):
        return

    files = []
    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            if filename.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, filename), folder)
                rel_path = rel_path.replace("\\", "/")
                files.append(rel_path)

    config_data = _sync_plugins_config(files)

    global _plugins_cache
    _plugins_cache = config_data

    for rel_path in files:
        conf       = config_data.get(rel_path, {})
        is_enabled = conf.get("toggle", True) if isinstance(conf, dict) else True
        if not is_enabled:
            continue
        try:
            path        = os.path.abspath(os.path.join(folder, rel_path))
            module_name = os.path.basename(rel_path)[:-3]
            spec        = importlib.util.spec_from_file_location(module_name, path)
            module      = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "on_search"):
                raw_keywords     = conf.get("keyword", [module_name]) if isinstance(conf, dict) else [module_name]
                module._keywords = [str(k).lower() for k in raw_keywords]
                module._limit    = int(conf.get("limit", 15)) if isinstance(conf, dict) else 15

                # Runtime safeguard: ensure always-global plugins have "*"
                # even if Plugins.json was generated before _ALWAYS_GLOBAL included them.
                if module_name.lower() in _ALWAYS_GLOBAL and "*" not in module._keywords:
                    module._keywords.append("*")

                loaded_plugins.append(module)
                dprint(f"Plugin loaded: {rel_path} (keywords: {module._keywords})")
        except Exception as e:
            eprint(f"Error loading plugin {rel_path}: {e}")


def load_all_modules():
    global loaded_plugins
    loaded_plugins = []
    _load_core(CORE_DIR)
    _load_plugins(PLUGINS_DIR)
    return loaded_plugins


# ──────────────────────────────────────────────
#  Plugin toggle (on_search exposed to the UI)
# ──────────────────────────────────────────────

def _toggle_plugin(name, current_status):
    try:
        with open(PLUGINS_FILE, "r") as f:
            data = json.load(f)
        if name in data:
            if isinstance(data[name], dict):
                data[name]["toggle"] = not current_status
            else:
                data[name] = not current_status
        with open(PLUGINS_FILE, "w") as f:
            json.dump(data, f, indent=4)
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        eprint(f"Error toggling plugin: {e}")


def on_search(text):
    results = []
    if _plugins_cache is None:
        return results
    data = _plugins_cache

    search_term = text.lower().strip()
    for name, conf in data.items():
        if search_term and search_term not in name.lower():
            continue

        is_enabled = conf.get("toggle", True) if isinstance(conf, dict) else conf
        status = "[ACTIVE]" if is_enabled else "[OFF]"
        results.append({
            "name":   f"{status} {name} (Press Enter to toggle)",
            "score":  1500,
            "action": lambda n=name, s=is_enabled: _toggle_plugin(n, s),
            "icon_type": "plugin"
        })
    return results
