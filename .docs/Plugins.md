# 📦 Plugins

<a href="Configuration.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Configuration</kbd></a>

## 🧩 Built-in plugins
Type `plugins` to list all loaded modules and toggle them on/off.

Or edit the `Plugins.json` file.

| Plugin | Description |
|---|---|
| <a href="Plugins/App.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">App</kbd></a> | Searches and launches installed applications |
| <a href="Plugins/Calc.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">Calc</kbd></a> | Evaluates math expressions and copies the result |
| <a href="Plugins/System.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">System</kbd></a> | Lock, sleep, restart, shutdown - with confirmation |
| <a href="Plugins/Shell.md" style="text-decoration:none"><kbd style="background:#1774ff;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">Shell</kbd></a> | Executes shell commands and manages named shortcuts |

# 📜 `Plugins.json`
Plugin management. Edit directly or via the `plugins` command inside InputBar.

```json
{
    "Calc.py": {
        "toggle": true,
        "keyword": [
            "calc",
            "*"
        ]
    },
    "System.py": {
        "toggle": true,
        "keyword": [
            "system",
            "*"
        ]
    },
    "App/App.py": {
        "toggle": true,
        "keyword": [
            "app",
            "*"
        ]
    },
    "Shell/Shell.py": {
        "toggle": true,
        "keyword": [
            "shell",
            "*"
        ]
    }
}
```

The `"*"` keyword means the plugin responds to all searches (global mode).  
Without `"*"`, the plugin only activates when the search starts with its keyword.
