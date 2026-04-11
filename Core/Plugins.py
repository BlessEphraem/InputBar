import os
import json
import sys
import importlib.util
from Core.Paths import PLUGINS_DIR, CORE_DIR, PLUGINS_FILE, CORE_FILE
from Core.Logging import dprint, eprint

loaded_plugins = []

def _sync_config_file(filepath, current_files, is_plugin):
    data = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f: data = json.load(f)
        except: data = {}

    new_data = {}
    # Safe migration from old JSON format (True) to new dictionary format
    for name, conf in data.items():
        if name in current_files:
            if isinstance(conf, bool):
                base_name = os.path.basename(name)[:-3]
                kws = [base_name.lower()]
                if is_plugin and base_name.lower() in ["app", "system"]:
                    kws.append("*")
                new_data[name] = {"toggle": conf, "keyword": kws}
            else:
                new_data[name] = conf

    for file in current_files:
        if file not in new_data:
            base_name = os.path.basename(file)[:-3]
            if is_plugin:
                default_keywords = [base_name.lower()]
                if base_name.lower() in ["app", "system"]:
                    default_keywords.append("*")
                new_data[file] = {
                    "toggle": True,
                    "keyword": default_keywords
                }

    with open(filepath, "w") as f: json.dump(new_data, f, indent=4)
    return new_data

def load_all_modules():
    global loaded_plugins
    loaded_plugins = []
    _load_folder(CORE_DIR, "Core", is_plugin=False)
    _load_folder(PLUGINS_DIR, "Plugin", is_plugin=True)
    return loaded_plugins

def _load_folder(folder, type_label, is_plugin=False):
    if not os.path.exists(folder): return

    files = []
    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            if filename.endswith(".py"):
                rel_path = os.path.relpath(os.path.join(root, filename), folder)
                rel_path = rel_path.replace("\\", "/")
                files.append(rel_path)

    filepath    = PLUGINS_FILE if is_plugin else CORE_FILE
    config_data = _sync_config_file(filepath, files, is_plugin)

    for rel_path in files:
        conf = config_data.get(rel_path, {})

        is_enabled = conf.get("toggle", True) if isinstance(conf, dict) else True
        if is_plugin and not is_enabled:
            continue

        try:
            path        = os.path.abspath(os.path.join(folder, rel_path))
            module_name = os.path.basename(rel_path)[:-3]
            spec        = importlib.util.spec_from_file_location(module_name, path)
            module      = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "on_search"):
                raw_keywords    = conf.get("keyword", [module_name]) if isinstance(conf, dict) else [module_name]
                module._keywords = [str(k).lower() for k in raw_keywords]

                loaded_plugins.append(module)
                dprint(f"{type_label} loaded: {rel_path} (Keywords: {module._keywords})")
        except Exception as e:
            eprint(f"Error loading {rel_path}: {e}")

def _toggle_plugin(name, current_status):
    try:
        with open(PLUGINS_FILE, "r") as f: data = json.load(f)
        if name in data:
            if isinstance(data[name], dict):
                data[name]["toggle"] = not current_status
            else:
                data[name] = not current_status  # Fallback for legacy format
        with open(PLUGINS_FILE, "w") as f: json.dump(data, f, indent=4)
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        eprint(f"Error toggling plugin: {e}")

def on_search(text):
    results = []
    try:
        with open(PLUGINS_FILE, "r") as f: data = json.load(f)
    except: return []

    search_term = text.lower().strip()
    for name, conf in data.items():
        if search_term and search_term not in name.lower():
            continue

        is_enabled = conf.get("toggle", True) if isinstance(conf, dict) else conf
        status = "[ACTIVE]" if is_enabled else "[OFF]"
        results.append({
            "name": f"{status} {name} (Press Enter to toggle)",
            "score": 1500,
            "action": lambda n=name, s=is_enabled: _toggle_plugin(n, s),
            "icon_type": "settings"
        })
    return results
