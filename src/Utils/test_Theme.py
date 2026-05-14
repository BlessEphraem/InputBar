"""
test_Theme.py — Automated unit tests for Theme._deep_merge().
Pure function — no file I/O, no GUI, no Core.Paths side-effects needed.

Run standalone:  python src/Utils/test_Theme.py
Exit 0 = all pass (True), Exit 1 = any failure (False).
"""
import os
import sys

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC_DIR)

from Core.Theme import _deep_merge

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
    print("[test_Theme] _deep_merge tests")

    default = {
        "color":  "black",
        "size":   12,
        "font":   {"family": "Arial", "weight": 400},
        "border": {"width": 1, "style": "solid"},
    }

    # User provides nothing → all defaults, was_updated=True
    merged, updated = _deep_merge(default, {})
    _check("empty user → all defaults present",     merged == default)
    _check("empty user → was_updated=True",         updated is True)

    # User provides all → no update needed, user values preserved
    full_user = {
        "color":  "red",
        "size":   18,
        "font":   {"family": "Segoe UI", "weight": 700},
        "border": {"width": 2, "style": "dashed"},
    }
    merged2, updated2 = _deep_merge(default, full_user)
    _check("full user → user values preserved",     merged2 == full_user)
    _check("full user → was_updated=False",         updated2 is False)

    # User provides partial → missing keys filled, existing kept
    partial_user = {"color": "blue"}
    merged3, updated3 = _deep_merge(default, partial_user)
    _check("partial: user color preserved",         merged3["color"]  == "blue")
    _check("partial: default size filled",          merged3["size"]   == 12)
    _check("partial: default font filled",          merged3["font"]   == {"family": "Arial", "weight": 400})
    _check("partial: was_updated=True",             updated3 is True)

    # Nested: user provides partial nested dict
    nested_user = {"font": {"family": "Verdana"}}  # missing weight
    merged4, updated4 = _deep_merge(default, nested_user)
    _check("nested: user font.family preserved",    merged4["font"]["family"] == "Verdana")
    _check("nested: missing font.weight filled",    merged4["font"]["weight"] == 400)
    _check("nested: was_updated=True",              updated4 is True)

    # Extra user keys not in default must be preserved
    extra_user = {"color": "green", "my_custom_key": "hello", "font": {"family": "Comic Sans", "weight": 400, "italic": True}}
    merged5, updated5 = _deep_merge(default, extra_user)
    _check("extra user key preserved at top level", merged5.get("my_custom_key") == "hello")
    _check("extra user key preserved in nested",    merged5["font"].get("italic") is True)

    # Immutability: original default not mutated
    original_default = {"x": 1, "nested": {"y": 2}}
    user_val         = {"x": 99}
    _deep_merge(original_default, user_val)
    _check("default dict not mutated",              original_default["x"] == 1)

    # Type mismatch: user has scalar where default has dict → user value wins (no crash)
    type_mismatch = {"color": "red", "font": "not_a_dict"}
    merged6, _ = _deep_merge(default, type_mismatch)
    _check("type mismatch: user scalar wins over default dict",
           merged6["font"] == "not_a_dict")

    ok = _fail == 0
    print(f"[test_Theme] {'PASSED' if ok else 'FAILED'} — {_pass} passed, {_fail} failed")
    for f in _fails:
        print(f"  x {f}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
