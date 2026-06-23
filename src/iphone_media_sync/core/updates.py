"""Check GitHub for a newer release than the running version."""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger(__name__)

GITHUB_OWNER = "n3yung-debug"
GITHUB_REPO = "iPhone-Media-Sync"
_LATEST_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def _parse_version(text: str) -> tuple[int, ...]:
    """Turn 'v1.2.3' / '1.2.3' into (1, 2, 3); non-numeric parts are dropped."""
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer(latest: str, current: str) -> bool:
    """True if ``latest`` is a strictly higher version than ``current``."""
    return _parse_version(latest) > _parse_version(current)


@dataclass
class UpdateInfo:
    latest: str
    url: str
    is_update: bool


def check_for_update(current_version: str, timeout: float = 5.0) -> Optional[UpdateInfo]:
    """Query the latest GitHub release. Returns None on any failure/offline."""
    try:
        req = urllib.request.Request(
            _LATEST_URL, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - network/parse, all non-fatal
        log.debug("update check failed: %s", exc)
        return None

    tag = data.get("tag_name") or ""
    url = data.get("html_url") or ""
    if not tag:
        return None
    return UpdateInfo(latest=tag, url=url, is_update=is_newer(tag, current_version))
