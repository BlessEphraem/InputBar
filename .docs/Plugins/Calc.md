# ➗ Plugin - Calc

<a href="../Plugins.md" style="text-decoration:none"><kbd style="background:#30363d;color:#e6edf3;border:none;padding:3px 10px;border-radius:5px">← Back to Plugins</kbd></a>

Evaluates mathematical expressions typed directly in InputBar and copies the result to the clipboard.

> **Keywords:** `calc` · `*` *(global — active on every search)* - [Edit in `Plugins.json`](../Plugins.md)

## Supported operations

| Operator | Meaning | Example |
|---|---|---|
| `+` | Addition | `12 + 8` → `20` |
| `-` | Subtraction | `100 - 37` → `63` |
| `*` | Multiplication | `6 * 7` → `42` |
| `/` | Division | `10 / 4` → `2.5` |
| `%` | Modulo | `17 % 5` → `2` |
| `^` or `**` | Power | `2 ^ 10` → `1024` |
| `()` | Grouping | `(3 + 4) * 2` → `14` |

Decimal numbers and negative values are supported:

```
-5 * (3.14 + 1)   → -20.7
2 ^ 32            → 4294967296
```

## Result

When a valid expression is detected, the result appears at the top of the list as `= <value>`.  
Pressing `Enter` copies the result to the clipboard.

Float results are rounded to 6 decimal places to avoid display noise.

## Safety

Expressions are evaluated using Python's `ast` module — **no `eval()` call is made**.  
Only numeric constants and the operators listed above are permitted. Any other input is silently ignored by the plugin.
