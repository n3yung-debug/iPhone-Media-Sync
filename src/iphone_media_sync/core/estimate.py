"""Pre-backup dry-run estimate: how much is new vs. already backed up."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..device.models import MediaItem


@dataclass
class BackupEstimate:
    total: int = 0
    new: int = 0
    already: int = 0
    bytes_new: int = 0

    @property
    def mb_new(self) -> float:
        return self.bytes_new / (1024 * 1024)

    def summary(self) -> str:
        return (
            f"{self.new} new item(s) to copy ({self.mb_new:.0f} MB); "
            f"{self.already} already backed up."
        )


def estimate_backup(items: Iterable[MediaItem]) -> BackupEstimate:
    """Estimate a backup of ``items`` using each item's ``backed_up`` flag."""
    est = BackupEstimate()
    for it in items:
        est.total += 1
        if it.backed_up:
            est.already += 1
        else:
            est.new += 1
            est.bytes_new += it.size or 0
    return est
