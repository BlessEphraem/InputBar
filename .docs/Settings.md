# 📜 `Settings.json`

[![](https://img.shields.io/badge/←_⚙️_Configuration-30363d?style=for-the-badge)](./Configuration.md)

> **Keywords:** settings · — type `settings` in InputBar to reload or open this file

Main InputBar settings. Located in `Data/Settings.json`, created automatically on first launch.  
On update, new keys are injected without overwriting your existing values.

```json
{
    "Position": "Center",
    "Monitor": 0,
    "AlwaysOnTop": true,
    "HideOnFocusLost": true,
    "HideOnPress": false,
    "LoopList": true,
    "Theme": "theme_default"
}
```

| Key | Type | Description |
|-----|------|-------------|
| `Position` | string | Window position: `Center`, `Top`, `Bottom`, `Left`, `Right`, `TopRight`, `BottomLeft`, `BottomRight`, `AtMouse` |
| `Monitor` | int | Monitor index (0 = primary) |
| `AlwaysOnTop` | bool | Stay above all other windows |
| `HideOnFocusLost` | bool | Close when the window loses focus |
| `HideOnPress` | bool / string | `false` = never closes on shortcut · `"OnFocus"` = closes if already active · `"Always"` = always closes |
| `LoopList` | bool | Loop navigation in the list (bottom → top and back) |
| `Theme` | string | Theme file name in `Data/Themes/` (without `.json`) |

> **Upgrading from an older version?** `Data/Config.json` (the previous settings file) is automatically migrated to `Data/Settings.json` on first launch and then deleted.
