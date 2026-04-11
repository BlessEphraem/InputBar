# Plugins.json

<a href="Configuration.md"><kbd>← Go back to Configuration page</kbd></a>

Plugin management. Edit directly or via the `plugin` command inside InputBar.

```json
{
    "App/App.py": {
        "toggle": true,
        "keyword": ["app", "*"]
    },
    "Calc.py": {
        "toggle": true,
        "keyword": ["calc", "*"]
    }
}
```

The `"*"` keyword means the plugin responds to all searches (global mode).  
Without `"*"`, the plugin only activates when the search starts with its keyword.


# Plugins/App/aliases.data

Define custom search aliases for the "App" plugin.

```
# Plugins/App/aliases.data

# Format: alias=app_name
pp=adobe premiere pro
ps=photoshop
vsc=visual studio code
```