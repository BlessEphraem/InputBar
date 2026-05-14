"""
test_Config.py — Tests for Path/Config.json read logic.
Mirrors the Paths.py ConfigDirectory resolution: absent/corrupted/empty file → ""
A clean reinstall deletes Config.json — this test verifies the fallback is correct.

Run standalone:  python src/Utils/test_Config.py
Exit 0 = all pass (True), Exit 1 = any failure (False).
"""
import os
import sys
import json
import tempfile

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC_DIR)

from Core.Paths import atomic_write_json

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


def _read_config_dir(config_path: str) -> str:
    """Mirrors Paths.py: read ConfigDirectory from Config.json, '' on any error/absence."""
    if not os.path.exists(config_path):
        return ""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("ConfigDirectory", "").strip()
    except Exception:
        return ""


def run() -> bool:
    print("[test_Config] Config.json read logic tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        path_dir    = os.path.join(tmpdir, "Path")
        os.makedirs(path_dir)
        config_file = os.path.join(path_dir, "Config.json")
        custom_dir  = os.path.join(tmpdir, "MyCustomData")

        # Absent → ""
        _check("absent Config.json → empty string",
               _read_config_dir(config_file) == "")

        # Valid ConfigDirectory
        atomic_write_json(config_file, {"ConfigDirectory": custom_dir})
        _check("valid ConfigDirectory → correct path",
               _read_config_dir(config_file) == custom_dir)

        # Empty string value
        atomic_write_json(config_file, {"ConfigDirectory": ""})
        _check("empty ConfigDirectory value → empty string",
               _read_config_dir(config_file) == "")

        # Whitespace-only value
        atomic_write_json(config_file, {"ConfigDirectory": "   "})
        _check("whitespace ConfigDirectory → empty string (stripped)",
               _read_config_dir(config_file) == "")

        # Key absent from JSON
        atomic_write_json(config_file, {"OtherKey": "value"})
        _check("missing ConfigDirectory key → empty string",
               _read_config_dir(config_file) == "")

        # Corrupted JSON
        with open(config_file, "w", encoding="utf-8") as f:
            f.write("not valid json {{{")
        _check("corrupted Config.json → empty string (no crash)",
               _read_config_dir(config_file) == "")

        # Clean reinstall scenario: Config.json deleted → must fall back to default
        atomic_write_json(config_file, {"ConfigDirectory": custom_dir})
        _check("pre-delete: path readable",
               _read_config_dir(config_file) == custom_dir)
        os.remove(config_file)
        _check("post-delete (clean reinstall): falls back to empty string",
               _read_config_dir(config_file) == "")

    ok = _fail == 0
    print(f"[test_Config] {'PASSED' if ok else 'FAILED'} — {_pass} passed, {_fail} failed")
    for f in _fails:
        print(f"  x {f}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
