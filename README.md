<div align="center">
  <h1 style="font-size: 3em; font-weight: 500">
  
【 𝗜𝗻𝗽𝘂𝘁 𝗕𝗮𝗿 】

  </h1>
</div>

<p align="center">
  <img src="./Assets/Icons/Logo.svg" width="300" alt="Premiere Companion">
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

# ✨ Features

- **App search** — fuzzy search across all installed apps (Start Menu, LOCALAPPDATA, Windows registry, UWP/Store)
- **Built-in calculator** — type `2 + 2`, the result appears and copies to clipboard
- **System commands** — lock, sleep, restart, shutdown (with confirmation step)
- **App submenu** — press right arrow on any app to access "Start as admin" / "Open folder"
- **Customizable shortcuts** — standard keys or Windows key via low-level hook
- **Fully themeable** — colors, borders, transparency via JSON
- **IPC pipe** — can be triggered from external scripts (AutoHotkey, etc.)
- **User data persistence** — updates inject new keys without overwriting existing settings

# 🚀 Installation

* ✅ **Recommended - Download the Setup / Portable version**
  1. Choose the "setup.exe" or the "portable.zip" from the [**Releases page**](https://github.com/BlessEphraem/InputBar/releases).
  2. Install or extract the files. The portable version is pre-packaged and ready to use out of the box.

* 🛠️ **From Source - Run the `.pyw` Script**

  If you prefer to run directly from source, clone this repository. Run your terminal as Administrator (required for global hotkeys and mouse simulation) and install the dependencies:
```Bash
pip install PyQt6 rapidfuzz pywin32
```

# ♟️ How to use

| Action | Shortcut |
|---|---|
| Open InputBar | `Ctrl+Space` *(default)* |
| Navigate results | `↑` / `↓` |
| Launch selection | `Enter` |
| Open app submenu | `→` |
| Go back | `←` or select "Back" |
| Close InputBar | `Escape` |

# ⚙️ Configuration
To keep the program as lightweight as possible, it does not include a Graphical User Interface (GUI). Instead, everything is managed through simple .json configuration files.

Don't worry if you're not a developer - configuring the app is straightforward! I've written detailed guides to walk you through the process step by step.

<a href=".docs/Configuration.md" style="text-decoration:none"><kbd style="background:#1f6feb;color:#fff;border:none;padding:3px 10px;border-radius:5px">→ Configuration Documentation</kbd></a>

## 🧩 App

Just start typing — InputBar fuzzy-searches all your installed apps instantly.

```
chrome    →  Google Chrome
vsc       →  Visual Studio Code  (via alias)
```

Press `→` on any result to access **Start as admin** or **Open folder**.

<a href=".docs/Plugins/App.md" style="text-decoration:none"><kbd style="background:#1f6feb;color:#fff;border:none;padding:3px 10px;border-radius:5px">→ App Documentation</kbd></a>

## 🧩 Calc

Type any math expression. The result appears at the top — press `Enter` to copy it.

```
(10 * 3) / 4  →  = 7.5
2 ^ 8         →  = 256
```

<a href=".docs/Plugins/Calc.md" style="text-decoration:none"><kbd style="background:#1f6feb;color:#fff;border:none;padding:3px 10px;border-radius:5px">→ Calc Documentation</kbd></a>

## 🧩 System

Type `system` or the command name directly. A confirmation is always required before execution.

```
lock      →  Lock the session
restart   →  Restart the PC
shutdown  →  Shut down
```

<a href=".docs/Plugins/System.md" style="text-decoration:none"><kbd style="background:#1f6feb;color:#fff;border:none;padding:3px 10px;border-radius:5px">→ System Documentation</kbd></a>

## 🧩 Shell

Type `shell` to list your saved shortcuts, or run commands directly from InputBar.

```
shell fastfetch       →  runs your "fastfetch" shortcut
git status            →  opens a terminal and runs git status
python C:\script.py   →  runs the script in a new window
```

<a href=".docs/Plugins/Shell.md" style="text-decoration:none"><kbd style="background:#1f6feb;color:#fff;border:none;padding:3px 10px;border-radius:5px">→ Shell Documentation</kbd></a>

---

# 🛠️ Tech Stack
- Python 3.11+
- PyQt6
- rapidfuzz
- pywin32  (optional — .lnk shortcut resolution + exe icon extraction)

# 📄 License

GPL-3.0 license - see [LICENSE](LICENSE) for details.
