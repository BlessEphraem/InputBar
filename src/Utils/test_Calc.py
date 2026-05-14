"""
test_Calc.py — Automated unit tests for the Calc plugin math evaluator.
Tests _safe_eval() (pure AST evaluator) and on_search() result filtering.
No Core dependencies — Calc.py is self-contained.

Run standalone:  python src/Utils/test_Calc.py
Exit 0 = all pass (True), Exit 1 = any failure (False).
"""
import os
import sys
import importlib.util

SRC_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_calc_path = os.path.join(SRC_DIR, "Plugins", "Calc.py")
_spec      = importlib.util.spec_from_file_location("Calc", _calc_path)
_calc      = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_calc)

_safe_eval = _calc._safe_eval
on_search  = _calc.on_search

import ast

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


def _eval(expr: str):
    return _safe_eval(ast.parse(expr, mode="eval"))


def run() -> bool:
    print("[test_Calc] _safe_eval arithmetic tests")

    _check("2 + 2 = 4",           _eval("2 + 2")      == 4)
    _check("10 - 3 = 7",          _eval("10 - 3")     == 7)
    _check("3 * 4 = 12",          _eval("3 * 4")      == 12)
    _check("10 / 4 = 2.5",        _eval("10 / 4")     == 2.5)
    _check("7 % 3 = 1",           _eval("7 % 3")      == 1)
    _check("2 ** 10 = 1024",      _eval("2 ** 10")    == 1024)
    _check("-5 (unary neg)",       _eval("-5")         == -5)
    _check("+3 (unary pos)",       _eval("+3")         == 3)
    _check("2 + 3 * 4 = 14 (precedence)", _eval("2 + 3 * 4") == 14)
    _check("(2 + 3) * 4 = 20",    _eval("(2 + 3) * 4") == 20)
    _check("1.5 + 2.5 = 4.0",     _eval("1.5 + 2.5") == 4.0)

    print("[test_Calc] _safe_eval rejection tests")

    def _raises(expr: str) -> bool:
        try:
            _eval(expr)
            return False
        except Exception:
            return True

    _check("string literal rejected",  _raises('"hello"'))
    _check("function call rejected",   _raises("abs(-1)"))
    _check("list literal rejected",    _raises("[1, 2]"))
    _check("name lookup rejected",     _raises("x"))

    print("[test_Calc] on_search result tests")

    # Should produce a result
    res = on_search("2 + 2")
    _check("'2 + 2' yields result",        len(res) == 1)
    _check("'2 + 2' result starts '= '",  res[0]["name"].startswith("= ") if res else False)
    _check("'2 + 2' result = '= 4'",      res[0]["name"] == "= 4" if res else False)

    res2 = on_search("10 / 4")
    _check("'10 / 4' yields '= 2.5'",     res2[0]["name"] == "= 2.5" if res2 else False)

    res3 = on_search("2^10")
    _check("'2^10' (caret) yields '= 1024'", res3[0]["name"] == "= 1024" if res3 else False)

    # Should NOT produce a result
    _check("plain text 'hello' → no result",       on_search("hello")       == [])
    _check("empty string → no result",             on_search("")            == [])
    _check("lone digit '5' → no result (no op)",   on_search("5")           == [])
    _check("letters+digits 'abc123' → no result",  on_search("abc123")      == [])

    # Float rounding — result should be clean (max 6 decimal places)
    res4 = on_search("1 / 3")
    if res4:
        val_str = res4[0]["name"][2:]  # strip "= "
        val     = float(val_str)
        _check("1/3 rounded to ≤6 decimals",
               len(val_str.split(".")[-1]) <= 6 if "." in val_str else True)
    else:
        _check("1/3 yields result", False)

    ok = _fail == 0
    print(f"[test_Calc] {'PASSED' if ok else 'FAILED'} — {_pass} passed, {_fail} failed")
    for f in _fails:
        print(f"  x {f}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
