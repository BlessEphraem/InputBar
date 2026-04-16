# 💠 Plugin - Shell

<a href="../Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Back to Plugins</kbd></a>

Executes shell commands and manages named command shortcuts (favorites).

> **Keywords:** `shell` · `*` *(global — active on every search)* - [Edit in `Plugins.json`](../Plugins.md)

## 📜 Default Shell - `default_shell.json`

Controls which shell is used when no [per-entry override](#Per-entry-shell-override) is set.

```json
{
    "default_shell": "cmd",
    "default_icon":  ""
}
```

| Key | Values | Description |
|---|---|---|
| `default_shell` | `"cmd"`, `"pwsh"`, `"powershell"` | Shell used by default |
| `default_icon` | `""` or absolute path to an image | Custom icon for all Shell results. Leave empty to use the bundled terminal icon. |

Changes to `default_shell.json` take effect immediately — no restart needed (the file is re-read on each command launch).

## ⭐ Favorites - `favorites.data`

Define named shortcuts for shell commands.

```
# favorites.data

# Format: key=command
#   key   — the name you search for in InputBar
#   value — the shell command to run (optionally prefixed with a shell name)

fastfetch=fastfetch
btop=btop
showFolder=ls "C:\My\Path\"
myscript=python C:\My\Path\script.py --arg
```

- Lines starting with `#` are comments and are ignored.
- Keys are case-insensitive.
- Search is fuzzy: typing `fast` will match `fastfetch`.

### Per-entry shell override

Prefix any entry's value with a shell name to override the default shell for that specific command:

```
btop=cmd btop            # runs btop in cmd, regardless of default shell
fastfetch=pwsh fastfetch # runs fastfetch in PowerShell 7
```

Supported shell prefixes: `cmd`, `pwsh`, `pwsh.exe`, `powershell`, `powershell.exe`


## ⚡ Direct shell commands

Any input that looks like a shell command is automatically detected and can be run directly, without defining a favorite first:

```
python C:\scripts\myscript.py --verbose
git status
C:\tools\mytool.exe --flag
```

You can also prefix with a shell name inline:

```
cmd btop
pwsh Get-Process | Sort-Object CPU -Descending
```

### Detection rules

An input is recognized as a shell command if it matches any of these conditions:

| Rule | Example |
|---|---|
| Contains a backslash `\` | `C:\tools\mytool.exe` |
| Contains a forward slash `/` | `./myscript.sh` |
| Starts with a known CLI prefix **and has at least one argument** | `git status`, `python script.py` |

Typing a prefix alone (e.g. just `git`) does **not** trigger the shell — an argument is required, to avoid interfering with app search.

**Recognized CLI prefixes:**

`python` `python3` `node` `npm` `npx` `git` `pip` `pip3` `cargo` `go` `java` `dotnet` `ruby` `perl` `bash` `sh` `pwsh` `powershell` `cmd` `code` `nvim` `vim`

## ♻️ Reloading favorites

After editing `favorites.data` or `default_shell.json`, reload without restarting InputBar:

1. Type `shell` in InputBar
2. Select **🔄 Shell: Reload favorites** and press `Enter`

Or type `shell reload` / `shell r` directly.

## 🌠 Custom Icon

The Shell plugin uses a bundled terminal icon (`Plugins/Shell/shell.svg`).  
To use a custom icon, set an absolute path in `default_icon` inside `default_shell.json`.
