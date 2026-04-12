"""
Utility: test_Version.py
------------------------
Forces an update notification exactly as InputBar would show it,
using version "1.0.0" as the installed version so the check always
triggers regardless of what is actually installed on this machine.

Run from the repo root:
    python src/Utils/test_Version.py
"""

import os
import sys

# __file__ = src/Utils/test_Version.py  →  dirname×2 = src/
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC_DIR)

from Core.Updater import _fetch_latest_version, _show_toast  # noqa: PLC2701

FORCED_CURRENT_VERSION = "1.0.0"
GITHUB_REPO            = "BlessEphraem/InputBar"


def main() -> None:
    print(f"[test_Version] Fetching latest release for {GITHUB_REPO} ...")
    latest = _fetch_latest_version(GITHUB_REPO)

    if latest is None:
        latest = "(network error)"
        print("[test_Version] Could not reach GitHub — showing error notification anyway")
    else:
        print(f"[test_Version] Latest release : {latest}")

    title       = "InputBar — Update available"
    message     = f"Version {latest} is available (you have {FORCED_CURRENT_VERSION})."
    release_url = f"https://github.com/{GITHUB_REPO}/releases/tag/{latest}"

    print(f"[test_Version] Firing toast: {title!r}")
    print(f"[test_Version] Release URL : {release_url}")
    _show_toast(title, message, url=release_url)
    print("[test_Version] Done.")


if __name__ == "__main__":
    main()
