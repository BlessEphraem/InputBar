# 💠 Plugin - Shell

<a href="../Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Back to Plugins</kbd></a>

Executes shell commands and manages named command shortcuts (favorites).

> **Keywords:** `shell` · `/` · `*` *(global — active on every search)* - [Edit in `Plugins.json`](../Plugins.md)

## 📜 Default Shell - `default_shell.json`

Controls which shell is used when no [per-entry override](#Per-entry-shell-override) is set.

```json
{
    "default_shell": "cmd",
    "default_icon":  "",
    "extra_shells":  {}
}
```

| Key | Values | Description |
|---|---|---|
| `default_shell` | `"cmd"`, `"pwsh"`, `"powershell"`, or any key from `extra_shells` | Shell used by default |
| `default_icon` | `""` or absolute path to an image | Custom icon for all Shell results. Leave empty to use the bundled terminal icon. |
| `extra_shells` | object — see below | Define custom terminal emulators |

Changes to `default_shell.json` take effect after restarting InputBar.

### Custom terminal emulators (`extra_shells`)

Define any terminal by giving it an alias and specifying how to launch it.  
The user command is appended as the last argument.

```json
"extra_shells": {
    "wezterm": ["wezterm.exe", "start", "--", "cmd.exe", "/k"]
}
```

This runs: `wezterm.exe start -- cmd.exe /k <your_command>`

To use WezTerm as your default shell:
```json
{
    "default_shell": "wezterm",
    "extra_shells": {
        "wezterm": ["wezterm.exe", "start", "--", "cmd.exe", "/k"]
    }
}
```

You can also use extra shell names as [per-entry overrides](#Per-entry-shell-override) in `favorites.data`:
```
fastfetch=wezterm fastfetch
```


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
colorpicker=C:\Scripts\Utils\ColorPicker.pyw
```

- Lines starting with `#` are comments and are ignored.
- Keys are case-insensitive.
- Search is fuzzy: typing `fast` will match `fastfetch`.

### Per-entry shell override

Prefix any entry's value with a shell name to override the default shell for that specific command:

```
btop=cmd btop            # runs btop in cmd, regardless of default shell
fastfetch=pwsh fastfetch # runs fastfetch in PowerShell 7
viewer=wezterm btop      # runs btop in WezTerm (defined in extra_shells)
```

Supported built-in prefixes: `cmd`, `pwsh`, `pwsh.exe`, `powershell`, `powershell.exe`  
Custom prefixes: any key defined in `extra_shells` inside `default_shell.json`.


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

Explicitly prefixing with `shell` or `/` always works for any command — including ones that wouldn't be auto-detected:

```
shell fastfetch        → runs fastfetch in your default shell
/ fastfetch            → same thing, shorter
/ htop                 → runs htop
```

### Detection rules (global mode)

An input is recognized as a shell command **without** the `shell` prefix if it matches:

| Rule | Example | Note |
|---|---|---|
| Contains `\` **and** at least one letter/digit | `C:\tools\mytool.exe` | Lone `\` does **not** trigger |
| Contains `/` **and** at least one letter/digit | `./myscript.sh` | Lone `/` does **not** trigger |
| Starts with a known CLI prefix **and has at least one argument** | `git status`, `python script.py` | Bare `git` alone does **not** trigger |

> If you want to run any arbitrary command, just type `shell <command>` or `/ <command>` — the keyword bypasses detection and always offers it as runnable.

**Recognized CLI prefixes:**

`python` `python3` `node` `npm` `npx` `git` `pip` `pip3` `cargo` `go` `java` `dotnet` `ruby` `perl` `bash` `sh` `pwsh` `powershell` `cmd` `code` `nvim` `vim`

## 🌠 Custom Icon

The Shell plugin uses a bundled terminal icon (`Plugins/Shell/shell.svg`).  
To use a custom icon, set an absolute path in `default_icon` inside `default_shell.json`.


## 💡 Examples

### Open a folder in Explorer

```
# favorites.data
projects=explorer C:\Dev\Projects
downloads=explorer %USERPROFILE%\Downloads
```

Type `proj` → Enter → Explorer opens directly on the folder.

---

### Run a command and keep the window open (default behavior)

The default shells (`cmd`, `pwsh`) always keep the window open after the command finishes so you can read the output.

```
# favorites.data
gitlog=git log --oneline -20
sysinfo=systeminfo
ipinfo=ipconfig /all
```

The terminal stays open — scroll, copy, done.

---

### Auto-close the window when the command succeeds

By default `cmd /k` keeps the window open. Define an `autoclose` shell using `cmd /c` instead — the window opens, runs the command, and disappears immediately.

`default_shell.json`:
```json
{
    "default_shell": "cmd",
    "extra_shells": {
        "autoclose": ["conhost.exe", "--", "cmd.exe", "/c"]
    }
}
```

`favorites.data`:
```
# Opens, runs, closes automatically
npminstall=autoclose npm install
gitpull=autoclose git pull
```

> Use `cmd /c` for commands where you don't need to read the output afterward.

---

### Run a command completely hidden (no window at all)

For background tasks where you don't want any visible terminal, use PowerShell's `-WindowStyle Hidden`:

`default_shell.json`:
```json
{
    "default_shell": "cmd",
    "extra_shells": {
        "silent": ["powershell.exe", "-WindowStyle", "Hidden", "-NonInteractive", "-Command"]
    }
}
```

`favorites.data`:
```
# Runs silently in the background — no window, no flash
gitadd=silent git -C C:\Dev\MyProject add .
backup=silent robocopy C:\Dev\MyProject D:\Backup\MyProject /MIR /NFL /NDL
syncnotes=silent python C:\Scripts\sync_notes.py
```

Type `gitadd` → Enter → nothing appears, `git add .` runs and exits cleanly.

> Useful for fire-and-forget tasks (backups, syncs, silent git operations).

---

### Git quick-commit in one shot

Chain multiple commands with `&&` so they run in sequence — if one fails, the chain stops.

```
# favorites.data
# Opens a cmd, stages everything, commits with a fixed message, pushes, then closes
quickpush=autoclose git -C C:\Dev\MyProject add . && git -C C:\Dev\MyProject commit -m "wip" && git -C C:\Dev\MyProject push
```

Or keep the window open to see each step:
```
gitdeploy=git -C C:\Dev\MyProject add . && git -C C:\Dev\MyProject commit -m "deploy" && git -C C:\Dev\MyProject push
```

---

### Launch a script and auto-close on success, stay open on error

Use `cmd /c` combined with a pause on error — the window disappears on success but stays visible if something goes wrong:

```
# favorites.data
runbuild=autoclose python C:\Dev\MyProject\build.py || pause
```

`||` means "run `pause` only if the previous command failed" — you see the error, press Enter, window closes.

---

### Open a terminal in a specific directory

`cd /d` changes drive and directory before running your shell:

`default_shell.json`:
```json
{
    "extra_shells": {
        "here": ["conhost.exe", "--", "cmd.exe", "/k", "cd /d"]
    }
}
```

`favorites.data`:
```
devterm=here C:\Dev\MyProject
scripts=here C:\Scripts
```

Type `devterm` → a terminal opens already positioned in `C:\Dev\MyProject`.
