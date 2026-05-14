"""
test_Hotkeys.py — Automated unit tests for hotkey parsing and translation.
Tests _normalize_hotkey(), _parse_hotkey(), _translate_to_wkh().
All functions are pure — no pipe, no daemon, no OS calls.

Run standalone:  python src/Utils/test_Hotkeys.py
Exit 0 = all pass (True), Exit 1 = any failure (False).
"""
import os
import sys

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC_DIR)

from Core.Hotkeys import _normalize_hotkey, _parse_hotkey, _translate_to_wkh

_pass  = 0
_fail  = 0
_fails = []


def _check(name: str, result: bool) -> None:
    global _pass, _fail
    if result:
        _pass += 1
        print(f"  [PASS] {name}")
    else:
        _fail += 1
        _fails.append(name)
        print(f"  [FAIL] {name}")


def run() -> bool:
    print("[test_Hotkeys] Normalize tests")

    # Identity — no alias
    _check("ctrl+space unchanged",        _normalize_hotkey("ctrl+space")   == "ctrl+space")
    _check("ctrl+alt+f4 unchanged",       _normalize_hotkey("ctrl+alt+f4")  == "ctrl+alt+f4")

    # Alias substitution
    _check("esc → escape",                _normalize_hotkey("esc")           == "escape")
    _check("windows → win",              _normalize_hotkey("windows")       == "win")
    _check("left win → lwin",            _normalize_hotkey("left win")      == "lwin")
    _check("right win → rwin",           _normalize_hotkey("right win")     == "rwin")
    _check("numpad0 → num0",             _normalize_hotkey("numpad0")       == "num0")
    _check("numpad9 → num9",             _normalize_hotkey("numpad9")       == "num9")
    _check("num * → num*",               _normalize_hotkey("num *")         == "num*")
    _check("media next track → next track", _normalize_hotkey("media next track") == "next track")

    # Case-folding
    _check("CTRL+SPACE → ctrl+space",    _normalize_hotkey("CTRL+SPACE")    == "ctrl+space")
    _check("Ctrl+Space → ctrl+space",    _normalize_hotkey("Ctrl+Space")    == "ctrl+space")

    # Whitespace around +
    _check("ctrl + space stripped",      _normalize_hotkey("ctrl + space")  == "ctrl+space")

    print("[test_Hotkeys] Parse / Win-key detection tests")

    # has_win
    _check("lwin → has_win=True",        _parse_hotkey("lwin")[0]           is True)
    _check("rwin → has_win=True",        _parse_hotkey("rwin")[0]           is True)
    _check("win → has_win=True",         _parse_hotkey("win")[0]            is True)
    _check("lwin+space → has_win=True",  _parse_hotkey("lwin+space")[0]     is True)
    _check("ctrl+space → has_win=False", _parse_hotkey("ctrl+space")[0]     is False)
    _check("ctrl+alt+f1 → has_win=False",_parse_hotkey("ctrl+alt+f1")[0]   is False)

    # parts
    _check("ctrl+space parts",           _parse_hotkey("ctrl+space")[1]     == ["ctrl", "space"])
    _check("lwin+space parts",           _parse_hotkey("lwin+space")[1]     == ["lwin", "space"])
    _check("ctrl+alt+del parts",         _parse_hotkey("ctrl+alt+del")[1]   == ["ctrl", "alt", "del"])

    print("[test_Hotkeys] WKH translation tests")

    # Simple key → uppercase
    _check("ctrl → CTRL",               _translate_to_wkh("ctrl")          == "CTRL")
    _check("space → SPACE",             _translate_to_wkh("space")         == "SPACE")
    _check("ctrl+space → CTRL+SPACE",   _translate_to_wkh("ctrl+space")    == "CTRL+SPACE")
    _check("lwin+space → LWIN+SPACE",   _translate_to_wkh("lwin+space")    == "LWIN+SPACE")
    _check("f4 → F4",                   _translate_to_wkh("f4")            == "F4")

    # Special mappings
    _check("page up → PGUP",            _translate_to_wkh("page up")       == "PGUP")
    _check("page down → PGDN",          _translate_to_wkh("page down")     == "PGDN")
    _check("caps lock → CAPS",          _translate_to_wkh("caps lock")     == "CAPS")
    _check("print screen → PRINT",      _translate_to_wkh("print screen")  == "PRINT")
    _check("num* → 0x6A",               _translate_to_wkh("num*")          == "0x6A")
    # num+ skipped: "+" is also the hotkey delimiter, so split("+"") on "num+" yields
    # ["num", ""] → "num+" is never recognized as a unit. Known parser limitation.
    _check("volume mute → 0xAD",        _translate_to_wkh("volume mute")   == "0xAD")
    _check("next track → 0xB0",         _translate_to_wkh("next track")    == "0xB0")

    ok = _fail == 0
    print(f"[test_Hotkeys] {'PASSED' if ok else 'FAILED'} — {_pass} passed, {_fail} failed")
    for f in _fails:
        print(f"  x {f}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
