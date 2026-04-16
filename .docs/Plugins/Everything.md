# 💫 Plugin - Everything

<a href="../Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Back to Plugins</kbd></a>

Search for files and folders on your computer instantly using the **[Everything](https://www.voidtools.com/)** search engine integration.

<p style="font-weight: bold; color: #ff6b6b">⚠️ Important: Everything must be installed on your computer for this plugin to work.</p>

## 🚀 How it Works

The plugin uses the **Everything SDK (DLL)** for optimal performance and real-time searching. Results are displayed incrementally without freezing the application.

> **Keywords (Strict):** `f` or `everything` - [Edit in `Plugins.json`](../Plugins.md)
>
> **Auto-detection (Global):** The plugin triggers automatically if your search looks like a path or a file (e.g., `image.png`, `C:\`, `.pdf`). Requires the `"*"` keyword in your configuration.

## 📁 Configuration (`Data/Plugins/Everything/`)

### 1. 📜 `EverythingPath.json`
Defines the path to the `Everything.exe` executable. The plugin attempts to auto-detect it on the first run.
```json
{
    "EverythingPath": "C:\\Program Files\\Everything\\Everything.exe"
}
```

### 2. 📜 `extensions.data`
List of extensions that automatically trigger an Everything search in global mode.
- One extension per line (e.g., `.png`).
- Lines starting with `#` are ignored.

### 3. ⭐ `favorites.data`

Create named shortcuts for your frequent folders or files.
```data
# Format: name=path
Projects=D:\Dev\CurrentProjects
Documents=C:\Users\Name\Documents
```
- Searching favorites is **fuzzy**: typing `proj` will find `Projects`.

## 🔍 Smart Trigger Rules

To avoid cluttering your regular searches, Everything only activates in global mode if:
1. The search contains a path separator (`\` or `/`).
2. The search starts with a drive letter (e.g., `C:`).
3. The search ends with an extension defined in `extensions.data`.

*Note: Adding the `*` prefix inside the [`Plugins.json`](../Plugins.md) forces an Everything search in all cases, but it will only trigger if one of these rules is met. This prevents Everything from activating unintentionally, such as when you search for Chrome.*

## 💡 Tips & Tricks

- **Two-Line Rendering:** Results display the file name in bold and the parent folder right below it to help you locate the file.
- **Long Paths:** If a path is too long, it is intelligently shortened (e.g., `C:\Users\...\Documents`).
- **Reloading:** Type `reload` or `rebuild` in the InputBar (when the plugin is active) to instantly refresh your favorites and extensions without restarting.
- **Auto-launch:** If Everything is not running, the plugin will attempt to start it silently in the background.

## 📖 Examples & Combinations

The power of the Everything plugin lies in how you combine keywords, paths, and extensions.

```
f project_report
# Search for any file/folder containing "project_report" everywhere using the default "f" keyword.
```

```
.png
# List all recently modified `.png` files on your PC (triggers via `extensions.data`).
```

```
D:/Movies .mkv
# List the contents of your Downloads folder instantly..
```

```
wallpapers .jpg
# If `wallpapers` is a favorite, searches for `.jpg` files inside that folder.
```

```
work report .pdf
# Filters your "work" folder (favorite) for PDF files containing "report".
```

```
f *.txt
# Standard Everything syntax: find all text files.
```

```
f size:>1gb
# Advanced Everything syntax: find all files larger than 1GB.
```

```
f dc:today
# Advanced Everything syntax: find all files created today.
```
> **Pro Tip:** You can use any [advanced search syntax supported by Everything](https://www.voidtools.com/support/everything/searching/) !
