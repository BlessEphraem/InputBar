# ⚙️ Configuration

**All configuration files live in the `Data/` folder** — created automatically on first launch.

<h3>🧩 App Settings</h3>
<ul>
    <li><h3><a href="Settings.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">📜 Settings</kbd></a></h3></li>
    <li><h3><a href="Hotkeys.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">⌨️ Hotkeys</kbd></a></h3></li>
    <li><h3><a href="Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">📦 Plugins</kbd></a></h3></li>
    <li><h3><a href="Theme.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">🎨 Theme</kbd></a></h3></li>
</ul>

<h3>💻 For Developers</h3>
<ul>
    <li><h3><a href="IPC.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">🛜 IPC</kbd></a></h3></li>
    <li><h3><a href="CreatePlugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">📦 Create a Plugin</kbd></a></h3></li>
</ul>

</br>

# 📁 `Config.json`

Located in `Path\Config.json`.  
Contains a single key that redirects where `Data/` and `Plugins/` are stored.

> Tip: Double the backslash '`\`' when specifying paths.
```json
{
    "ConfigDirectory": "C:\\Users\\YourName\\AppData\\Roaming\\InputBar"
}
```

| Key | Type | Description |
|-----|------|-------------|
| `ConfigDirectory` | string | Absolute path to use as the base for `Data/` and `Plugins/`. Leave empty or at the default path to use the standard location next to the executable. |

## How the redirect works

When InputBar starts and reads a non-empty `ConfigDirectory`, two scenarios apply:

### The target path is empty (or does not exist yet)

InputBar starts fresh at the new location:
- The full directory tree is created automatically
- Missing plugin seed files are copied from the built-in defaults:
  - `Plugins/App/aliases.data`
  - `Plugins/Shell/favorites.data`
  - `Plugins/Shell/default_shell.json`
- Default settings are written on first launch

### The target path already contains an InputBar configuration

InputBar adopts it immediately — nothing is overwritten:
- Missing sub-directories are created (`Data/Themes/`, `Plugins/App/`, …)
- Plugin data files that are already present are left untouched
- Any new settings keys added in this version are injected on first read
- The old location is ignored from that point on

This is the expected path when you point `ConfigDirectory` to a backup, a shared drive, or a location you populated manually beforehand.

**In both cases, your data at the old location is never touched.**  
If you want to carry it over, copy the files below before restarting:

| File | What it contains |
|------|-----------------|
| `Data\Settings.json` | All app settings (position, theme, hotkeys…) |
| `Data\Plugins.json` | Plugin enable / disable state |
| `Data\search_history.json` | Search history and frecency scores |
| `Data\Themes\` | Custom theme files |
| `Plugins\App\aliases.data` | App aliases |
| `Plugins\Shell\favorites.data` | Shell command favorites |
| `Plugins\Shell\default_shell.json` | Default shell preference |
| `Plugins\Everything\favorites.data` | Everything folder shortcuts |
| `Plugins\Everything\extensions.data` | Everything auto-trigger extensions |

> The old location is left untouched. InputBar will simply ignore it once `ConfigDirectory` points elsewhere.
