# Writing a plugin

<a href="Configuration.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Configuration</kbd></a>

## Clone the repository

Create a destination folder for the project, then open your preferred terminal or command prompt (e.g., CMD, PowerShell, or Git Bash). Run the following commands, making sure to replace the placeholder path with your actual folder directory:

```Bash
cd "C:\Your\Folder\Path\"
git clone https://github.com/BlessEphraem/InputBar
```

Before running the application, you need to install the required Python packages. You can easily do this using pip:
```Bash
pip install PyQt6 rapidfuzz keyboard pywin32
```

## Write a plugin

A plugin is a `.py` file in `Plugins/` that exposes an `on_search(text) -> list` function.

```python
# Plugins/MyPlugin.py

def on_search(text: str) -> list:
    if "hello" not in text.lower():
        return []
    return [{
        "name": "Hello World",
        "score": 100,
        "action": lambda: print("Hello!"),
        "icon_type": "settings",   # "file" | "calc" | "settings"
    }]
```

Each returned item can have:

| Field | Type | Description |
|---|---|---|
| `name` | str | Text displayed in the list |
| `score` | float | Sort score (higher = listed first) |
| `action` | str or callable | Path to open or function to call |
| `icon_type` | str | Icon style: `"file"`, `"calc"`, `"settings"` |
| `icon_path` | str | Path to a custom icon (optional) |
| `item_type` | str | Set to `"app"` to enable the right-arrow submenu |

If `action` returns the string `"KEEP_OPEN_AND_REFRESH"`, InputBar stays open and refreshes the results — useful for confirmation flows.

---
