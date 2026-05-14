"""
test_Version.py — Automated unit tests for Core.Updater version logic.
Tests _parse_version() and update comparison — no network call, no GUI.

Run standalone:  python src/Utils/test_Version.py
Exit 0 = all pass (True), Exit 1 = any failure (False).
"""
import os
import sys

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC_DIR)

from Core.Updater import _parse_version

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
    print("[test_Version] Version parser tests")

    # Parsing
    _check("parse '1.2.3'",          _parse_version("1.2.3")      == (1, 2, 3))
    _check("parse 'v1.2.3'",         _parse_version("v1.2.3")     == (1, 2, 3))
    _check("parse '2.0.0'",          _parse_version("2.0.0")      == (2, 0, 0))
    _check("parse '0.0.1'",          _parse_version("0.0.1")      == (0, 0, 1))
    _check("parse '10.20.30'",       _parse_version("10.20.30")   == (10, 20, 30))
    _check("parse bad → (0,)",       _parse_version("not_a_ver")  == (0,))
    _check("parse empty → (0,)",     _parse_version("")            == (0,))

    # Comparison
    _check("1.3.0 > 1.2.0",          _parse_version("1.3.0")  >  _parse_version("1.2.0"))
    _check("2.0.0 > 1.9.9",          _parse_version("2.0.0")  >  _parse_version("1.9.9"))
    _check("1.0.1 > 1.0.0",          _parse_version("1.0.1")  >  _parse_version("1.0.0"))
    _check("1.0.0 == 1.0.0",         _parse_version("1.0.0")  == _parse_version("1.0.0"))
    _check("1.0.0 not > 1.0.0",  not (_parse_version("1.0.0") >  _parse_version("1.0.0")))
    _check("1.0.0 not > 2.0.0",  not (_parse_version("1.0.0") >  _parse_version("2.0.0")))
    _check("v prefix equality",       _parse_version("v2.0.0") == _parse_version("2.0.0"))

    ok = _fail == 0
    print(f"[test_Version] {'PASSED' if ok else 'FAILED'} — {_pass} passed, {_fail} failed")
    for f in _fails:
        print(f"  x {f}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
