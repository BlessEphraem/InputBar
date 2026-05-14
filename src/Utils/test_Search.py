"""
test_Search.py — Automated unit tests for Core.Search routing logic.
Tests process_search() strict mode, global mode, and single-char prefix matching.
Uses mock plugins — no real plugins loaded, no filesystem access.

Run standalone:  python src/Utils/test_Search.py
Exit 0 = all pass (True), Exit 1 = any failure (False).
"""
import os
import sys

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC_DIR)

from Core.Search import process_search

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


class _MockPlugin:
    """Minimal plugin stub for routing tests."""
    def __init__(self, name: str, keywords: list[str], results: list[dict] | None = None):
        self.__name__  = name
        self._keywords = keywords
        self._limit    = 15
        self.received  = []
        self._results  = results or [{"name": f"{name}_result", "score": 100}]

    def on_search(self, text: str) -> list[dict]:
        self.received.append(text)
        return list(self._results)


def run() -> bool:
    print("[test_Search] Strict mode routing tests")

    calc   = _MockPlugin("Calc",  ["calc", "*"])
    shell  = _MockPlugin("Shell", ["shell", "/", "*"])
    app    = _MockPlugin("App",   ["app", "*"])

    plugins = [calc, shell, app]

    # Strict: "calc" prefix routes only to Calc
    results = list(process_search("calc foo", plugins))
    _check("'calc foo' → Calc called",          len(calc.received) == 1)
    _check("'calc foo' → Shell not called",     len(shell.received) == 0)
    _check("'calc foo' → App not called",       len(app.received) == 0)
    _check("'calc foo' → payload stripped",     calc.received[0] == "foo")
    _check("'calc foo' → returns results",      len(results) > 0)

    calc.received.clear()
    shell.received.clear()
    app.received.clear()

    # Strict: "shell" prefix routes only to Shell
    list(process_search("shell ls -la", plugins))
    _check("'shell ls -la' → Shell called",    len(shell.received) == 1)
    _check("'shell ls -la' → Calc not called", len(calc.received)  == 0)
    _check("'shell ls -la' → payload stripped",shell.received[0]   == "ls -la")

    calc.received.clear()
    shell.received.clear()
    app.received.clear()

    print("[test_Search] Global mode routing tests")

    # Global: no keyword match → all * plugins called
    list(process_search("notepad", plugins))
    _check("global: Calc (*) called",          len(calc.received)  == 1)
    _check("global: Shell (*) called",         len(shell.received) == 1)
    _check("global: App (*) called",           len(app.received)   == 1)
    _check("global: full query passed",        calc.received[0]    == "notepad")
    _check("global: full query to Shell",      shell.received[0]   == "notepad")

    calc.received.clear()
    shell.received.clear()
    app.received.clear()

    print("[test_Search] Single-char non-alnum prefix tests")

    # "/" prefix on Shell — no space needed
    list(process_search("/fastfetch", plugins))
    _check("'/fastfetch' → Shell called (/ prefix)", len(shell.received) == 1)
    _check("'/fastfetch' → Calc not called",         len(calc.received)  == 0)
    _check("'/fastfetch' → App not called",          len(app.received)   == 0)
    _check("'/fastfetch' → payload stripped",        shell.received[0]   == "fastfetch")

    calc.received.clear()
    shell.received.clear()
    app.received.clear()

    print("[test_Search] History score injection tests")

    # Score must be injected into each result (even if history is empty → score stays as-is)
    results2 = list(process_search("calc 2+2", plugins))
    _check("result has 'score' field",              all("score" in r for r in results2))

    print("[test_Search] Limit tests")

    many = _MockPlugin("Many", ["many"], [{"name": f"r{i}", "score": i} for i in range(50)])
    many._limit = 5
    results3 = list(process_search("many x", [many]))
    _check("limit=5 caps results at 5",             len(results3) == 5)

    ok = _fail == 0
    print(f"[test_Search] {'PASSED' if ok else 'FAILED'} — {_pass} passed, {_fail} failed")
    for f in _fails:
        print(f"  x {f}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
