<div align="center">
  <h1 style="font-size: 3em; font-weight: 500">
  
【 𝗜𝗻𝗽𝘂𝘁 𝗕𝗮𝗿 】

  </h1>
</div>

<p align="center">
  <img src="./Assets/Icons/Logo.svg" width="300" alt="InputBar">
</p>

<p align="center">
  <a href="https://github.com/BlessEphraem/InputBar/releases">
    <img src="https://img.shields.io/github/v/release/BlessEphraem/InputBar?style=flat-square&color=blue&v=2" alt="Latest Release">
  </a>
  <img src="https://img.shields.io/badge/OS-Windows-0078D6?style=flat-square&logo=windows&logoColor=white&v=2" alt="Windows Only">
  <a href="https://github.com/BlessEphraem/InputBar/releases">
    <img src="https://img.shields.io/github/downloads/BlessEphraem/InputBar/total?style=flat-square&color=success" alt="Downloads">
  </a>
  <a href="https://github.com/BlessEphraem/InputBar/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/BlessEphraem/InputBar?style=flat-square&v=2" alt="License">
  </a>
</p>

A fast application launcher for Windows, triggered by a global keyboard shortcut.  
Minimal interface, plugin-based, fully configurable through JSON files.

<p align="center">
  <img src=".docs/medias/preview_InputBar.png" width="100%" alt="Preview Search Bar">
</p>

---

## ✨ Features

- **App search** — fuzzy search across all installed apps (Start Menu, LOCALAPPDATA, Windows registry, UWP/Store)
- **File search** — integrates [voidtools Everything](https://www.voidtools.com/) for instant file and folder search
- **Built-in calculator** — type `2 + 2`, the result appears and copies to clipboard
- **System commands** — lock, sleep, restart, shutdown (with confirmation step)
- **Result submenu** — press `→` on any app or file to access Start as admin / Open folder / Copy file path
- **Shell shortcuts** — named command shortcuts with fuzzy search, per-entry shell override
- **Customizable shortcuts** — standard keys or Windows key via low-level hook
- **Fully themeable** — colors, borders, transparency, icon tints via JSON
- **IPC pipe** — can be triggered from external scripts (AutoHotkey, etc.)
- **User data persistence** — updates inject new keys without overwriting existing settings

## 🚀 Installation

* ✅ **Setup / Portable**  
  Download the `Setup.exe` or `Portable.zip` from the [**Releases page**](https://blessephraem.github.io/wiki/programs/inputbar/releases).

* ✅ **Winget**
  ```
  winget install Ephraem.InputBar
  ```

* 🛠️ **From Source**

  Clone the repository, then install the dependencies:
  ```bash
  pip install PyQt6 rapidfuzz pywin32
  ```
  Run `src/InputBar.pyw` (as Administrator for global hotkeys).

## ♟️ How to use

| Action | Shortcut |
|---|---|
| Open InputBar | `Ctrl+Space` *(default)* |
| Navigate results | `↑` / `↓` |
| Launch selection | `Enter` |
| Open submenu | `→` |
| Go back | `←` or select "Back" |
| Close InputBar | `Escape` |

<!-- wiki-hide-start -->

<a href="https://blessephraem.github.io/wiki/programs/inputbar">
  <img src="https://capsule-render.vercel.app/api?type=soft&color=278BF5&height=120&text=%F0%9F%8C%90%20%F0%9D%90%96%F0%9D%90%88%F0%9D%90%8A%F0%9D%90%88%20%F0%9F%8C%90&fontColor=ffffff&fontSize=45" alt="Wiki Banner">
</a>

<!-- wiki-hide-end -->

## ⚙️ Configuration
Everything is managed through JSON files — no settings GUI.

[![](https://img.shields.io/badge/→_⚙️_Configuration-30363d?style=for-the-badge)](https://blessephraem.github.io/wiki/programs/inputbar/configuration)

## 🧩 App

Just start typing — InputBar fuzzy-searches all your installed apps instantly.

```
chrome    →  Google Chrome
vsc       →  Visual Studio Code  (via alias)
```

Press `→` on any result to access **Start as admin**, **Open folder**, or **Copy file path**.

[![](https://img.shields.io/badge/→_🧩_App_Documentation-32C73E?style=for-the-badge)](https://blessephraem.github.io/wiki/programs/inputbar/plugins/app)

## 🧩 Everything (file search)

Requires [voidtools Everything](https://www.voidtools.com/) — started silently in the background if not running.

```
f report.pdf          →  search "report.pdf" everywhere
Z:\Projects           →  list all files in that folder
wallpapers .png       →  search .png files in your "wallpapers" favorite folder
.mp4                  →  list recently modified .mp4 files
```

Define folder shortcuts in `Plugins/Everything/favorites.data`:
```
wallpapers=C:\Users\Me\Pictures\Wallpapers
projects=D:\Dev\Projects
```

[![](https://img.shields.io/badge/→_🧩_Everything_Documentation-32C73E?style=for-the-badge)](https://blessephraem.github.io/wiki/programs/inputbar/plugins/everything)

## 🧩 Calc

Type any math expression. The result appears at the top — press `Enter` to copy it.

```
(10 * 3) / 4  →  = 7.5
2 ^ 8         →  = 256
```
[![](https://img.shields.io/badge/→_🧩_Calc_Documentation-32C73E?style=for-the-badge)](https://blessephraem.github.io/wiki/programs/inputbar/plugins/calc)

## 🧩 System

Type `system` or the command name directly. A confirmation is always required before execution.

```
lock      →  Lock the session
restart   →  Restart the PC
shutdown  →  Shut down
```

[![](https://img.shields.io/badge/→_🧩_System_Documentation-32C73E?style=for-the-badge)](https://blessephraem.github.io/wiki/programs/inputbar/plugins/system)

## 🧩 Shell

Type `shell` to list your saved shortcuts, or run commands directly from InputBar.

```
shell fastfetch       →  runs your "fastfetch" shortcut
git status            →  opens a terminal and runs git status
python C:\script.py   →  runs the script in a new window
```

Define shortcuts in `Plugins/Shell/favorites.data`:
```
btop=cmd btop
fastfetch=pwsh fastfetch
```

[![](https://img.shields.io/badge/→_🧩_Shell_Documentation-32C73E?style=for-the-badge)](https://blessephraem.github.io/wiki/programs/inputbar/plugins/shell)

---

## 🛠️ Tech Stack
- Python 3.11+
- PyQt6
- rapidfuzz
- pywin32  (optional — .lnk shortcut resolution + exe icon extraction)

## 📄 License

GPL-3.0 license - see [LICENSE](LICENSE) for details.
