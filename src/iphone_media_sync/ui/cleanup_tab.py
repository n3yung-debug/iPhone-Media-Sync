"""Free-up-space tab: review phone media and mark items to delete from device.

Nothing is deleted without an explicit confirmation. By default only items that
are verified-backed-up may be checked, so you can't accidentally remove the only
copy of a photo. Cleanup-candidate buttons pre-select likely-removable items
(screenshots, blurry photos, large videos) for you to review.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..device.models import MediaKind
from .filter_bar import FilterBar
from .thumbnail_grid import MediaGrid

_ROLE = Qt.ItemDataRole.UserRole


class CleanupTab(QWidget):
    delete_clicked = Signal()

    def __init__(self, require_backup: bool = True, blurry_threshold: float = 50.0,
                 large_video_mb: int = 200, parent=None):
        super().__init__(parent)
        self._require_backup = require_backup
        self._blurry_threshold = blurry_threshold
        self._large_video_mb = large_video_mb
        self.grid = MediaGrid()
        self.filter = FilterBar()
        self.filter.changed.connect(self._apply_filter)

        self._summary = QLabel("Connect an iPhone to begin.")
        self.only_backed_up = QCheckBox("Only show items already backed up")
        self.only_backed_up.setChecked(True)
        self.only_backed_up.stateChanged.connect(self._apply_filter)

        top = QHBoxLayout()
        top.addWidget(self._summary)
        top.addStretch(1)
        top.addWidget(self.only_backed_up)

        # Cleanup-candidate quick-selectors.
        cand = QHBoxLayout()
        cand.addWidget(QLabel("Select candidates:"))
        self.btn_shots = QPushButton("Screenshots")
        self.btn_blurry = QPushButton("Blurry photos")
        self.btn_large = QPushButton("Large videos")
        self.btn_shots.clicked.connect(lambda: self._select_candidates("screenshot"))
        self.btn_blurry.clicked.connect(lambda: self._select_candidates("blurry"))
        self.btn_large.clicked.connect(lambda: self._select_candidates("large_video"))
        select_none = QPushButton("Uncheck all")
        select_none.clicked.connect(lambda: self.grid.set_all_checked(False))
        cand.addWidget(self.btn_shots)
        cand.addWidget(self.btn_blurry)
        cand.addWidget(self.btn_large)
        cand.addStretch(1)
        cand.addWidget(select_none)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self._status = QLabel("")

        self.delete_btn = QPushButton("Delete checked from phone…")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self.delete_clicked)

        bottom = QHBoxLayout()
        bottom.addWidget(self._status, 1)
        bottom.addWidget(self.delete_btn)

        warn = QLabel(
            "⚠ Deletion is permanent. After deleting, the Photos app may briefly "
            "show empty thumbnails until the phone re-indexes."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("color: #c8a000;")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.filter)
        layout.addLayout(cand)
        layout.addWidget(self.grid, 1)
        layout.addWidget(warn)
        layout.addWidget(self.progress)
        layout.addLayout(bottom)

        self.grid.selection_changed.connect(self._update_summary)

    def populate(self, items) -> None:
        self.grid.clear_items()
        self.grid.add_items(items, checked=False)
        self._apply_filter()
        self._update_summary()

    def set_thresholds(self, blurry_threshold: float, large_video_mb: int) -> None:
        self._blurry_threshold = blurry_threshold
        self._large_video_mb = large_video_mb

    def set_require_backup(self, require: bool) -> None:
        self._require_backup = require

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def set_busy(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.delete_btn.setEnabled(not busy and bool(self.grid.checked_items()))

    # -- helpers ----------------------------------------------------------
    def _eligible(self, media) -> bool:
        return media.backed_up or not self._require_backup

    def _is_candidate(self, media, kind: str) -> bool:
        if kind == "screenshot":
            return media.is_screenshot
        if kind == "blurry":
            return (
                media.kind == MediaKind.PHOTO
                and not media.is_screenshot
                and media.sharpness is not None
                and media.sharpness < self._blurry_threshold
            )
        if kind == "large_video":
            return (
                media.kind == MediaKind.VIDEO
                and (media.size or 0) >= self._large_video_mb * 1024 * 1024
            )
        return False

    def _select_candidates(self, kind: str) -> None:
        matched = 0
        self.grid.blockSignals(True)
        for i in range(self.grid.count()):
            it = self.grid.item(i)
            media = it.data(_ROLE)
            if (not it.isHidden() and self._eligible(media)
                    and self._is_candidate(media, kind)):
                it.setCheckState(Qt.CheckState.Checked)
                matched += 1
        self.grid.blockSignals(False)
        self._update_summary()
        if matched == 0:
            self._status.setText(f"No eligible {kind.replace('_', ' ')} found.")

    def _apply_filter(self) -> None:
        only = self.only_backed_up.isChecked()
        for i in range(self.grid.count()):
            it = self.grid.item(i)
            media = it.data(_ROLE)
            hide = (only and not media.backed_up) or not self.filter.matches(media)
            it.setHidden(hide)
            if hide:
                it.setCheckState(Qt.CheckState.Unchecked)

    def _update_summary(self) -> None:
        checked = self.grid.checked_items()
        mb = sum(m.size for m in checked) / (1024 * 1024)
        self._summary.setText(f"{len(checked)} item(s) marked · {mb:.0f} MB to free")
        self.delete_btn.setEnabled(bool(checked))
