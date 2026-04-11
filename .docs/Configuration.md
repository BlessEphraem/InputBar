# Configuration

**All configuration files live in the `Data/` folder.**

<h3>🧩 Basic Configuration</h3>
They are created automatically on first launch with default values.  
On update, new keys are injected without touching existing user values.
<ul>
    <li><h3><a href="Hotkeys.md">⌨️ Hotkeys </a></h3></li>
    <li><h3><a href="Plugins.md">📦 Plugins </a></h3></li>
    <li><h3><a href="Theme.md">🖌️ Theme </a></h3></li>
</ul>

<h3>💻 For Developpers</h3>
<ul>
    <li><h3><a href="IPC.md">🛜 IPC</a></h3></li>
    <li><h3><a href="CreatePlugins.md">📦 Create a Plugin</a></h3></li>
</ul>

## Config.json
General InputBar settings.

```json
{
    "Position": "Center",
    "Monitor": 0,
    "AlwaysOnTop": true,
    "HideOnFocusLost": true,
    "HideOnPress": false,
    "LoopList": true,
    "ListMax": 200
}
```

| Key | Type | Description |
|---|---|---|
| `Position` | string | Window position: `Center`, `Top`, `Bottom`, `Left`, `Right`, `TopRight`, `BottomLeft`, `BottomRight`, `AtMouse` |
| `Monitor` | int | Monitor index (0 = primary) |
| `AlwaysOnTop` | bool | Stay above all other windows |
| `HideOnFocusLost` | bool | Close when the window loses focus |
| `HideOnPress` | bool / string | `false` = never closes on shortcut, `"OnFocus"` = closes if already active, `"Always"` = always closes |
| `LoopList` | bool | Loop navigation in the list (bottom → top and back) |
| `ListMax` | int | Maximum number of results displayed (max 200) |
