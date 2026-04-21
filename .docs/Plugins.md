# 📦 Plugins

[![](https://img.shields.io/badge/←_⚙️_Configuration-30363d?style=for-the-badge)](./Configuration.md)

## 🧩 Built-in plugins
Type `plugins` to list all loaded modules and toggle them on/off.

Or edit the `Plugins.json` file.

| Plugin | Description |
|---|---|
| <a href="Plugins/App.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">App</kbd></a> | Searches and launches installed applications |
| <a href="Plugins/Calc.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">Calc</kbd></a> | Evaluates math expressions and copies the result |
| <a href="Plugins/System.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">System</kbd></a> | Lock, sleep, restart, shutdown - with confirmation |
| <a href="Plugins/Shell.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">Shell</kbd></a> | Executes shell commands and manages named shortcuts |
| <a href="Plugins/Everything.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">Everything</kbd></a> | Searches through your folders |

## 📜 `Plugins.json`
Plugin management. Edit directly or via the `plugins` command inside InputBar.

```json
{
    "Calc.py": {
        "toggle": true,
        "keyword": ["calc", "*"],
        "limit": 15
    },
    "System.py": {
        "toggle": true,
        "keyword": ["system", "*"],
        "limit": 15
    },
    "App/App.py": {
        "toggle": true,
        "keyword": ["app", "*"],
        "limit": 15
    },
    "Shell/Shell.py": {
        "toggle": true,
        "keyword": ["shell", "*"],
        "limit": 15
    },
    "Everything/Everything.py": {
        "toggle": true,
        "keyword": ["everything", "f", "*"],
        "limit": 15
    }
}
```

| Key | Type | Description |
|-----|------|-------------|
| `toggle` | bool | Enable or disable the plugin |
| `keyword` | list | Keywords that trigger the plugin. `"*"` = responds to every query (global mode). Without `"*"`, the plugin only activates when the search starts with its keyword |
| `limit` | int | Maximum number of results this plugin can return (default `15`) |
