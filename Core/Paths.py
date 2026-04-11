import os
import sys
import argparse
import tempfile
import re

# Parse global arguments
parser = argparse.ArgumentParser()
parser.add_argument('--search', type=str, help="Text to pre-fill in the search bar")
parser.add_argument('--config', type=str, help="Custom root path for Data and Plugins")
args, unknown = parser.parse_known_args()

IS_CLI_MODE     = bool(args.search)
CLI_SEARCH_TEXT = args.search if args.search else ""

# SCRIPT_DIR is the parent of the "Core" directory
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if getattr(sys, 'frozen', False):
    # Compiled mode: Data/ lives next to InputBar.exe
    BASE_DIR = os.path.dirname(sys.executable)
elif args.config:
    BASE_DIR = os.path.abspath(args.config)
else:
    BASE_DIR = SCRIPT_DIR

# Directories
CORE_DIR   = os.path.join(SCRIPT_DIR, "Core")
DATA_DIR   = os.path.join(BASE_DIR, "Data")
THEMES_DIR = os.path.join(DATA_DIR, "Themes")
CACHE_DIR  = os.path.join(DATA_DIR, "__pycache__")

# In frozen mode SCRIPT_DIR == Lib/ (_MEIPASS), so Plugins/ is inside Lib/.
# In dev mode Plugins/ sits next to the source root.
if getattr(sys, 'frozen', False):
    PLUGINS_DIR = os.path.join(SCRIPT_DIR, "Plugins")
else:
    PLUGINS_DIR = os.path.join(BASE_DIR, "Plugins")

# Built-in themes bundled with the app (read-only source)
if getattr(sys, 'frozen', False):
    BUILTIN_THEMES_DIR = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)), 'Assets', 'Themes')
else:
    BUILTIN_THEMES_DIR = os.path.join(SCRIPT_DIR, 'Assets', 'Themes')

for folder in [CORE_DIR, DATA_DIR, THEMES_DIR, PLUGINS_DIR, CACHE_DIR]:
    if not os.path.exists(folder):
        try: os.makedirs(folder)
        except: pass

# Data files
HISTORY_FILE = os.path.join(DATA_DIR, "search_history.json")
PLUGINS_FILE = os.path.join(DATA_DIR, "Plugins.json")
CONFIG_FILE  = os.path.join(DATA_DIR, "Config.json")

LOG_FILE = os.path.join(tempfile.gettempdir(), "InputBar.log")


def get_plugin_temp_path(plugin_name, item_name):
    """
    Generates the absolute path for a plugin's temporary data file.
    Example: InputBar_Effects_History.tmp
    """
    if plugin_name.lower().endswith('.py'):
        plugin_name = plugin_name[:-3]

    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '', plugin_name)
    clean_item = re.sub(r'[^a-zA-Z0-9_-]', '', item_name)
    temp_dir   = tempfile.gettempdir()

    return os.path.join(temp_dir, f"InputBar_{clean_name}_{clean_item}.tmp")


def write_plugin_temp_result(plugin_name, content):
    """
    Creates a standardised temporary file for the specified plugin's result in %TEMP%.
    Returns the absolute path of the created file.
    """
    temp_filepath = get_plugin_temp_path(plugin_name, "result")

    try:
        with open(temp_filepath, "w", encoding="utf-8") as f:
            f.write(str(content))
        return temp_filepath
    except Exception as e:
        from Core.Logging import eprint
        eprint(f"Error writing temp file for {plugin_name}: {e}")
        return None
