# Hotkeys.json

<a href="Configuration.md"><kbd>← Go back to Configuration page</kbd></a>

A huge shout-out to my friend [@vlad-samp](https://github.com/vlad-samp).
Without him, implementing a low-level hook to intercept the Windows key wouldn't have been possible.

Global keyboard shortcuts.

```json
{
    "show_inputbar": "ctrl+space"
}
```

| Key | Description |
|---|---|
| `show_inputbar` | Shortcut to show/hide InputBar |

---

## How to write a shortcut

A shortcut is a string made of **one or more keys joined by `+`**.

```bash
{modifier} + {key}
{modifier} + {modifier} + {key}
{single key}
```

**Examples:**

```json
"ctrl+space"
"ctrl+alt+p"
"alt+f1"
"f13"
"win"
"lwin+space"
```

---

## Modifier keys

These are the keys you hold while pressing another.

| Value | Alias | Key |
|---|---|---|
| `ctrl` | | Ctrl (left or right) |
| `lctrl` | `left ctrl` | Left Ctrl only |
| `rctrl` | `right ctrl` | Right Ctrl only |
|---|---|---|
| `alt` | | Alt (left or right) |
| `lalt` | `left alt` | Left Alt only |
| `ralt` | `right alt` | Right Alt only |
|---|---|---|
| `shift` | | Shift (left or right) |
| `lshift` | `left shift` | Left Shift only |
| `rshift` | `right shift` | Right Shift only |
|---|---|---|
| `win` | | Windows key (left or right) ⚠️ |
| `lwin` | `left win` | Windows key (left only) ⚠️ |
| `rwin` | `right win` | Windows key (right only) ⚠️ |

> **Aliases:** Both forms are accepted and automatically normalised to the short form in `hotkeys.json`.

> **Windows key:** When `win`, `lwin`, or `rwin` is part of the shortcut, InputBar automatically launches a background process (`winkey_hook.exe`) that intercepts the key at system level, preventing the Start Menu from opening. The process is completely invisible.

---

#### Regular keys

Combine these with a modifier, or use them alone.

**Letters**

```
a b c d e f g h i j k l m n o p q r s t u v w x y z
```

**Numbers (top row)**

```
0 1 2 3 4 5 6 7 8 9
```

**Function keys**

```
f1  f2  f3  f4  f5  f6
f7  f8  f9  f10 f11 f12
f13 f14 f15 f16 f17 f18 f19 f20
```

> `f13`–`f20` are supported on extended keyboards. Useful for assigning InputBar without conflicting with anything.

**Navigation & editing**

| Value | Key |
|---|---|
| `space` | Space bar |
| `tab` | Tab |
| `enter` | Enter |
| `backspace` | Backspace |
| `delete` | Delete |
| `insert` | Insert |
| `home` | Home |
| `end` | End |
| `page up` | Page Up |
| `page down` | Page Down |
| `up` | Arrow Up |
| `down` | Arrow Down |
| `left` | Arrow Left |
| `right` | Arrow Right |
| `escape` | Escape |
| `caps lock` | Caps Lock |
| `print screen` | Print Screen |
| `scroll lock` | Scroll Lock |
| `pause` | Pause / Break |

**Numpad**

| Value | Alias | Key |
|---|---|---|
| `num0` – `num9` | `numpad0` – `numpad9` | Numpad 0 to 9 |
| `num+` | `num +` | Numpad + |
| `num-` | `num -` | Numpad − |
| `num*` | `num *` | Numpad × |
| `num/` | `num /` | Numpad ÷ |
| `num.` | `num .` | Numpad . |
| `num enter` | | Numpad Enter |

**Media keys** *(on supported keyboards)*

| Value | Alias | Key |
|---|---|---|
| `play/pause` | `media play/pause` | Play / Pause |
| `next track` | `media next track` | Next track |
| `previous track` | `media prev track` | Previous track |
| `stop` | `media stop` | Stop |
| `volume up` | | Volume up |
| `volume down` | | Volume down |
| `volume mute` | | Mute |

---

#### Recommended shortcuts

| Shortcut | Notes |
|---|---|
| `ctrl+space` | Default. Clean, rarely conflicts |
| `alt+space` | Common launcher convention |
| `ctrl+alt+space` | Safe if `alt+space` is taken |
| `f13` | Silent and conflict-free on extended keyboards |
| `win` | Replaces the Start Menu entirely |
| `lwin+space` | Windows key + Space — natural feel |

---