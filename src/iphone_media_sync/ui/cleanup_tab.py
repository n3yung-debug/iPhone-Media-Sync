"""Free-up-space tab: review phone media and mark items to delete from device.

Nothing is deleted without an explicit confirmation. By default only items that
are verified-backed-up may be checked, so you can't accidentally remove the only
copy of a photo.
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

from .thumbnail_grid import MediaGrid


class CleanupTab(QWidget):
    delete_clicked = Signal()

    def __init__(self, require_backup: bool = True, parent=None):
        super().__init__(parent)
        self._require_backup = require_backup
        self.grid = MediaGrid()

        self._summary = QLabel("Connect an iPhone to begin.")
        self.only_backed_up = QCheckBox("Only show items already backed up")
        self.only_backed_up.setChecked(True)
        self.only_backed_up.stateChanged.connect(self._apply_filter)

        select_all = QPushButton("Check all shown")
        select_none = QPushButton("Uncheck all")
        select_all.clicked.connect(self._check_all_eligible)
        select_none.clicked.connect(lambda: self.grid.set_all_checked(False))

        top = QHBoxLayout()
        top.addWidget(self._summary)
        top.addStretch(1)
        top.addWidget(self.only_backed_up)
        top.addWidget(select_all)
        top.addWidget(select_none)

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

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def set_busy(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.delete_btn.setEnabled(not busy and bool(self.grid.checked_items()))

    def _eligible(self, media) -> bool:
        return media.backed_up or not self._require_backup

    def _check_all_eligible(self) -> None:
        self.grid.blockSignals(True)
        for i in range(self.grid.count()):
            it = self.grid.item(i)
            media = it.data(Qt.ItemDataRole.UserRole)
            if not it.isHidden() and self._eligible(media):
                it.setCheckState(Qt.CheckState.Checked)
        self.grid.blockSignals(False)
        self._update_summary()

    def _apply_filter(self) -> None:
        only = self.only_backed_up.isChecked()
        for i in range(self.grid.count()):
            it = self.grid.item(i)
            media = it.data(Qt.ItemDataRole.UserRole)
            hide = only and not media.backed_up
            it.setHidden(hide)
            if hide:
                it.setCheckState(Qt.CheckState.Unchecked)

    def _update_summary(self) -> None:
        checked = self.grid.checked_items()
        mb = sum(m.size for m in checked) / (1024 * 1024)
        self._summary.setText(
            f"{len(checked)} item(s) marked · {mb:.0f} MB to free"
        )
        self.delete_btn.setEnabled(bool(checked))
