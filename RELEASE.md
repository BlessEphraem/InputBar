# **RELEASE NOTE: 1.2.3**

## Data Directory Management

- **Choose your data location at install time** — A new step in the installer lets you pick where InputBar stores its settings, themes and history. Leave it as-is to keep data in the install folder (default behaviour).
- **Config path change detection** — If you redirect `Path\Config.json` to a new location and restart InputBar, a dialog will offer to move your existing data there automatically.
- **Old data cleanup** — If you decline the move, a second dialog lets you delete the now-unused data instead of leaving it behind.
- **Dead data detection** — On startup, if your active data directory differs from the install folder, InputBar checks for leftover `Data\` and `Plugins\` directories in the install folder and offers to remove them.
