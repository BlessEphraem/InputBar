# 🚀 Plugin - App

<a href="../Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Back to Plugins</kbd></a>

Searches and launches installed applications — Win32, UWP (Microsoft Store), and shortcuts.

> **Keywords:** `app` · `*` *(global — active on every search)* - [Edit in `Plugins.json`](../Plugins.md)

## 🔎 Indexing

At startup, the App plugin builds a search index from three sources:

| Source | What's included |
|---|---|
| `.lnk` shortcuts | Start Menu (system + user), Desktop |
| UWP / Store apps | Via `Get-StartApps` (PowerShell) |
| Registry | `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths` |

Typing anything searches across all indexed apps using a 4-pass fuzzy strategy:

1. **Acronym match** — `vsc` matches `Visual Studio Code`
2. **Substring match** — `chrome` matches `Google Chrome`
3. **Fuzzy WRatio** — handles typos and partial words
4. **Partial ratio** — fallback for short queries

Results are sorted by match quality. Frequently launched apps are boosted via usage history.

---

## 📜 Aliases — `aliases.data`

Define custom shorthand names for apps. Useful for apps with long or inconsistent names.

```
# aliases.data

# Format: alias=app_name
pp=adobe premiere pro
ps=photoshop
vsc=visual studio code
cmd=command prompt
pwsh=powershell
```

- The alias maps to the app's display name (as it appears in the index).
- Aliases are case-insensitive.
- Multiple aliases can point to the same app.

