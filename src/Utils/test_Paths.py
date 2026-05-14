"""
test_Paths.py — Automated unit tests for Core.Paths security and utility functions.
Tests _is_safe_config_path() and atomic_write_json().

Run standalone:  python src/Utils/test_Paths.py
Exit 0 = all pass (True), Exit 1 = any failure (False).
"""
import os
import sys
import json
import tempfile

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC_DIR)

from Core.Paths import _is_safe_config_path, atomic_write_json

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
    print("[test_Paths] Path security tests")

    userprofile = os.environ.get("USERPROFILE", os.path.expanduser("~"))

    # Safe paths — must be accepted
    _check("user home accepted",
           _is_safe_config_path(userprofile))
    _check("temp dir accepted",
           _is_safe_config_path(tempfile.gettempdir()))
    _check(".config subdir accepted",
           _is_safe_config_path(os.path.join(userprofile, ".config", "MyApp")))
    _check("AppData\\Roaming accepted",
           _is_safe_config_path(os.path.join(userprofile, "AppData", "Roaming", "MyApp")))

    # System paths — must be rejected
    windows_root = os.environ.get("SystemRoot", "C:\\Windows")
    _check("SystemRoot rejected",
           not _is_safe_config_path(windows_root))
    _check("System32 rejected",
           not _is_safe_config_path(os.path.join(windows_root, "System32")))
    _check("C:\\Windows literal rejected",
           not _is_safe_config_path("C:\\Windows"))
    _check("Program Files rejected",
           not _is_safe_config_path(os.environ.get("ProgramFiles", "C:\\Program Files")))

    # UNC paths — must be rejected
    _check("UNC \\\\server\\share rejected",
           not _is_safe_config_path("\\\\server\\share"))
    _check("UNC \\\\127.0.0.1\\c$ rejected",
           not _is_safe_config_path("\\\\127.0.0.1\\c$"))

    # Traversal attempts — must be rejected (resolve into system dir)
    _check("traversal into Windows rejected",
           not _is_safe_config_path("C:\\Windows\\..\\Windows"))

    # atomic_write_json
    print("[test_Paths] Atomic write tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "out.json")
        data   = {"key": "value", "num": 42, "nested": {"a": 1}}

        atomic_write_json(target, data)

        _check("file created after write",
               os.path.exists(target))
        _check("tmp file cleaned up",
               not os.path.exists(target + ".tmp"))

        with open(target, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        _check("content round-trips correctly",
               loaded == data)

        # Overwrite must replace content atomically
        data2 = {"updated": True, "v": 2}
        atomic_write_json(target, data2)
        with open(target, "r", encoding="utf-8") as f:
            loaded2 = json.load(f)
        _check("overwrite produces new content",
               loaded2 == data2)
        _check("old content not present after overwrite",
               "key" not in loaded2)

        # Subdir creation: target in non-existent subdir
        nested_target = os.path.join(tmpdir, "sub", "deep", "file.json")
        atomic_write_json(nested_target, {"ok": True})
        _check("creates missing subdirectories",
               os.path.exists(nested_target))

    ok = _fail == 0
    print(f"[test_Paths] {'PASSED' if ok else 'FAILED'} — {_pass} passed, {_fail} failed")
    for f in _fails:
        print(f"  x {f}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
