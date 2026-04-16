# 💫 Plugin - Everything

<a href="../Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Back to Plugins</kbd></a>

Use Everything to search files/folders on your computer.
<p style="font-weight: bold; color: red">⚠️ Everything not included, it must be installed. </a>

> **Keywords:** `f` - [Edit in `Plugins.json`](../Plugins.md)

> **Exceptions:** Everything can be triggered when filepath or extension ar. (E,g. ``image.png``, ``bloc.txt``, ``C:\``..) See more in `Everything/extensions.data`

## 📜 Everything Path - `EverythingPath.json`

```json
{
    "EverythingPath": "C:\\Program Files\\Everything\\Everything.exe"
}
```

## 📜 Extensions - `extensions.data`

```data
    # Everything Plugin — Extensions
    # Extensions listed here trigger a file search automatically when typed in InputBar.
    # One extension per line. Lines starting with '#' are ignored.
    # Warning: You must add "*" as a keyword for the Everything plugin in `Plugins.json` for this feature to work.

    # Documents
    .pdf
    .doc
    .docx
    .txt
    .rtf
    .odt
    .md
    .csv
    .xls
    .xlsx
    .ppt
    .pptx

    # Images
    .png
    .jpg
    .jpeg
    .gif
    .svg
    .webp
    .bmp
    .ico
    .tiff

    # Videos
    .mp4
    .mkv
    .avi
    .mov
    .wmv
    .webm
    .flv

    # Audio
    .mp3
    .wav
    .flac
    .ogg
    .m4a
    .aac

    # Archives
    .zip
    .rar
    .7z
    .tar
    .gz
    .iso

    # Code & Web
    .json
    .xml
    .html
    .css
    .js
    .ts
    .py
    .java
    .cpp
    .c
    .cs
    .php
    .sql
    .yml
    .yaml

    # System & Scripts
    .exe
    .msi
    .bat
    .cmd
    .ps1
    .sh
    .ini
    .cfg
    .dll
    .lnk
```

## ⭐ Favorites - `favorites.data`

Define named folders/files for fast search.

```
# favorites.data

# Format: key=file/folder path
#   key              — the name you search for in InputBar
#   file/folder path — the file/folder path to run/search in
MyFolder=Z:\Random\User\Path
```

- Lines starting with `#` are comments and are ignored.
- Keys are case-insensitive.
- Search is fuzzy: typing `fast` will match `fastfetch`.

### Detection rules

An input is recognized as a Everything command if it matches any of these conditions:

| Rule | Example |
|---|---|
| Contains a backslash `\` | `C:\tools\mytool.exe` |
| Contains a forward slash `/` | `./myscript.sh` |
| Extensions file (see `extensions.data`) | .mp4, .png, .ico.. |

