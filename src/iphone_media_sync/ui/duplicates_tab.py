"""Duplicates tab: review duplicate groups and decide which copies to drop.

For each group the largest (best-quality) copy is suggested as the one to keep;
the rest are pre-checked. Checked copies can be excluded from the backup and/or
deleted from the phone — but only after you've reviewed them here.
"""

from __future__ import annotations


from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.dedupe import DuplicateGroup
from ..device.models import MediaItem
from .thumbnail_grid import MediaGrid


class DuplicatesTab(QWidget):
    find_clicked = Signal(int)  # threshold
    exclude_clicked = Signal(list)  # list[MediaItem] to drop from backup
    delete_clicked = Signal(list)  # list[MediaItem] to delete from phone

    def __init__(self, threshold: int = 5, parent=None):
        super().__init__(parent)
        self._group_grids: list[MediaGrid] = []
        self._thumb_cache: dict[str, QImage] = {}

        self._summary = QLabel("Run analysis on the Backup tab first, then find duplicates.")
        self.threshold = QSpinBox()
        self.threshold.setRange(0, 20)
        self.threshold.setValue(threshold)
        self.threshold.setPrefix("similarity ≤ ")
        self.threshold.setToolTip(
            "How visually similar two photos must be to count as near-duplicates.\n"
            "0 = identical only; higher = looser matching."
        )
        self.find_btn = QPushButton("Find duplicates")
        self.find_btn.clicked.connect(lambda: self.find_clicked.emit(self.threshold.value()))

        top = QHBoxLayout()
        top.addWidget(self._summary, 1)
        top.addWidget(self.threshold)
        top.addWidget(self.find_btn)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._container)

        self.exclude_btn = QPushButton("Exclude checked copies from backup")
        self.delete_btn = QPushButton("Delete checked copies from phone…")
        self.exclude_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.exclude_btn.clicked.connect(lambda: self.exclude_clicked.emit(self._checked()))
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self._checked()))

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(self.exclude_btn)
        bottom.addWidget(self.delete_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(scroll, 1)
        layout.addLayout(bottom)

    def set_thumb_cache(self, cache: dict[str, QImage]) -> None:
        self._thumb_cache = cache

    def show_groups(self, groups: list[DuplicateGroup]) -> None:
        self._clear_groups()
        if not groups:
            self._summary.setText("No duplicates found. 🎉")
            self.exclude_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            return

        total_save = sum(g.removable_bytes for g in groups)
        self._summary.setText(
            f"{len(groups)} duplicate group(s) · up to {total_save / (1024*1024):.0f} MB "
            f"recoverable. Checked copies are the ones marked to drop."
        )
        self.exclude_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        insert_at = self._container_layout.count() - 1  # before the stretch
        for gi, group in enumerate(groups):
            self._container_layout.insertWidget(insert_at + gi, self._build_group(gi, group))

    # -- internals --------------------------------------------------------
    def _build_group(self, index: int, group: DuplicateGroup) -> QWidget:
        kind = "Exact duplicate" if group.exact else "Similar photos"
        header = QLabel(
            f"{kind} · {len(group.items)} copies · "
            f"save {group.removable_bytes / (1024*1024):.1f} MB"
        )
        header.setStyleSheet("font-weight: bold;")

        grid = MediaGrid()
        grid.setFlow(MediaGrid.Flow.LeftToRight)
        grid.setWrapping(False)
        grid.setFixedHeight(240)
        grid.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for i, media in enumerate(group.items):
            keep = i == group.suggested_keep
            grid.add_item(media, checked=not keep)  # checked = drop this copy
            if keep:
                last = grid.item(grid.count() - 1)
                last.setText("⭐ keep · " + media.filename)
            cached = self._thumb_cache.get(media.afc_path)
            if cached is not None:
                grid.set_thumbnail(media.afc_path, cached)
        self._group_grids.append(grid)

        box = QWidget()
        v = QVBoxLayout(box)
        v.addWidget(header)
        v.addWidget(grid)
        return box

    def _checked(self) -> list[MediaItem]:
        out: list[MediaItem] = []
        for grid in self._group_grids:
            out.extend(grid.checked_items())
        return out

    def _clear_groups(self) -> None:
        self._group_grids.clear()
        # Remove every widget except the trailing stretch.
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
