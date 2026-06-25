"""Backup tab: review the camera roll and copy selected media to disk."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .filter_bar import FilterBar
from .thumbnail_grid import MediaGrid


class BackupTab(QWidget):
    backup_clicked = Signal()
    cancel_clicked = Signal()
    retry_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid = MediaGrid()
        self.filter = FilterBar()
        self.filter.changed.connect(self._refilter)

        self._summary = QLabel("Connect an iPhone to begin.")
        select_all = QPushButton("Select all")
        select_none = QPushButton("Select none")
        check_sel = QPushButton("Check selected")
        check_sel.setToolTip("Check the highlighted tiles (ctrl/shift-click to multi-select).")
        invert = QPushButton("Invert")
        select_all.clicked.connect(lambda: self.grid.set_all_checked(True))
        select_none.clicked.connect(lambda: self.grid.set_all_checked(False))
        check_sel.clicked.connect(lambda: self.grid.check_selected(True))
        invert.clicked.connect(self.grid.invert_checks)

        top = QHBoxLayout()
        top.addWidget(self._summary)
        top.addStretch(1)
        top.addWidget(check_sel)
        top.addWidget(invert)
        top.addWidget(select_all)
        top.addWidget(select_none)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self._status = QLabel("")

        self.retry_btn = QPushButton("Retry failed")
        self.retry_btn.setVisible(False)
        self.retry_btn.clicked.connect(self.retry_clicked)
        self.backup_btn = QPushButton("Back up selected")
        self.backup_btn.setEnabled(False)
        self.backup_btn.clicked.connect(self.backup_clicked)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_clicked)

        bottom = QHBoxLayout()
        bottom.addWidget(self._status, 1)
        bottom.addWidget(self.retry_btn)
        bottom.addWidget(self.cancel_btn)
        bottom.addWidget(self.backup_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.filter)
        layout.addWidget(self.grid, 1)
        layout.addWidget(self.progress)
        layout.addLayout(bottom)

        self.grid.selection_changed.connect(self._update_summary)

    # -- state ------------------------------------------------------------
    def set_summary(self, text: str) -> None:
        self._summary.setText(text)

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def set_busy(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.cancel_btn.setVisible(busy)
        self.backup_btn.setEnabled(not busy and self.grid.count() > 0)

    def set_ready(self, ready: bool) -> None:
        self.backup_btn.setEnabled(ready and self.grid.count() > 0)

    def show_retry(self, count: int) -> None:
        self.retry_btn.setVisible(count > 0)
        self.retry_btn.setText(f"Retry {count} failed" if count else "Retry failed")

    def _refilter(self) -> None:
        self.grid.apply_filter(self.filter.matches)
        self.grid.sort_by(self.filter.sort_key(), self.filter.sort_reverse())

    def _update_summary(self) -> None:
        total = self.grid.count()
        chosen = len(self.grid.checked_items())
        self._summary.setText(f"{chosen} of {total} selected to back up")
