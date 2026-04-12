"""
Update checker — runs once at startup in a background thread.
Compares the installed version against the latest GitHub release and
shows a Windows toast notification if an update is available.
"""

import subprocess
import threading
import urllib.request
import urllib.error
import json
from Core.Logging import dprint, eprint


def _parse_version(version_string: str) -> tuple[int, ...]:
    """Convert '1.2.3' or 'v1.2.3' to (1, 2, 3) for comparison."""
    clean = version_string.lstrip("v").strip()
    try:
        return tuple(int(x) for x in clean.split("."))
    except ValueError:
        return (0,)


def _fetch_latest_version(github_repo: str) -> str | None:
    """
    Query the GitHub Releases API for the latest release tag.
    Returns the version string (e.g. '1.2.0') or None on any error.
    """
    url = f"https://api.github.com/repos/{github_repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "InputBar-UpdateChecker/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            return tag.lstrip("v").strip() if tag else None
    except urllib.error.HTTPError as e:
        if e.code != 404:
            eprint(f"Updater: HTTP error {e.code} fetching latest release")
    except Exception as e:
        eprint(f"Updater: failed to fetch latest release — {e}")
    return None


def _show_toast(title: str, body: str, url: str | None = None) -> None:
    """
    Display a modern Windows 10/11 toast notification via PowerShell WinRT.
    Registers 'InputBar' in HKCU so Windows accepts the toast, then fires it.
    If url is provided, a 'Download' button is added that opens it in the browser.
    Fires-and-forgets; never raises.
    """
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace("'", "''")
    safe_body  = body.replace("&", "&amp;").replace("<", "&lt;").replace("'", "''")

    actions_xml = (
        f'<actions><action content="Download" activationType="protocol" arguments="{url}"/></actions>'
        if url else ""
    )

    # Windows silently drops toasts from unregistered app IDs.
    # We register InputBar under HKCU\SOFTWARE\Classes\AppUserModelId first.
    script = (
        "$appId = 'InputBar';"
        " $reg = \"HKCU:\\SOFTWARE\\Classes\\AppUserModelId\\$appId\";"
        " New-Item -Path $reg -Force | Out-Null;"
        " Set-ItemProperty -Path $reg -Name 'DisplayName' -Value 'InputBar';"
        " [void][Windows.UI.Notifications.ToastNotificationManager,"
        " Windows.UI.Notifications, ContentType=WindowsRuntime];"
        " [void][Windows.Data.Xml.Dom.XmlDocument,"
        " Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime];"
        " $xml = New-Object Windows.Data.Xml.Dom.XmlDocument;"
        f" $xml.LoadXml('<toast><visual><binding template=\"ToastGeneric\">"
        f"<text>{safe_title}</text>"
        f"<text>{safe_body}</text>"
        f"</binding></visual>{actions_xml}</toast>');"
        " $toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
        " [Windows.UI.Notifications.ToastNotificationManager]"
        "::CreateToastNotifier($appId).Show($toast)"
    )

    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception as e:
        eprint(f"Updater: failed to show toast notification — {e}")


def _run_check(current_version: str, github_repo: str) -> None:
    """Background worker: fetch latest version and show toast if outdated."""
    dprint(f"Updater: checking for updates (current={current_version}, repo={github_repo})")
    latest = _fetch_latest_version(github_repo)

    if latest is None:
        dprint("Updater: could not retrieve latest version, skipping")
        return

    dprint(f"Updater: latest release is {latest}")

    if _parse_version(latest) > _parse_version(current_version):
        dprint(f"Updater: update available ({current_version} → {latest})")
        release_url = f"https://github.com/{github_repo}/releases/tag/{latest}"
        _show_toast(
            "InputBar — Update available",
            f"Version {latest} is available (you have {current_version}).",
            url=release_url,
        )
    else:
        dprint("Updater: already up to date")


def check_for_updates_async() -> None:
    """
    Launch a one-shot background update check.
    Safe to call even if _version.py does not exist (dev mode without a build).
    """
    try:
        from Core._version import APP_VERSION, GITHUB_REPO
    except ImportError:
        dprint("Updater: _version.py not found (dev mode), skipping update check")
        return

    if APP_VERSION.endswith("-dev") or APP_VERSION == "0.0.0":
        dprint("Updater: dev build, skipping update check")
        return

    thread = threading.Thread(
        target=_run_check,
        args=(APP_VERSION, GITHUB_REPO),
        daemon=True,
        name="InputBar-UpdateChecker",
    )
    thread.start()
