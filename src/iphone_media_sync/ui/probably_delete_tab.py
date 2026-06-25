"""Probably Delete tab: surfaces likely-ephemeral images for review.

Screenshots of messages, memes, and images saved from the web/chats are
usually used in the moment and not worth long-term storage. This tab scores
each photo and lists the likely candidates (checked by default) for you to
review and delete. Nothing is deleted without confirmation.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.classify import ephemeral_score
from ..device.models import MediaItem
from .thumbnail_grid import MediaGrid

_ROLE = Qt.ItemDataRole.UserRole


class ProbablyDeleteTab(QWidget):
    delete_clicked = Signal()
    ocr_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_items: list[MediaItem] = []
        self._thumb_cache: dict[str, QImage] = {}
        self.grid = MediaGrid()

        self._summary = QLabel("Connect an iPhone and let analysis finish.")
        self.sensitivity = QSpinBox()
        self.sensitivity.setRange(0, 100)
        self.sensitivity.setValue(50)
        self.sensitivity.setSuffix("% sensitivity")
        self.sensitivity.setToolTip(
            "Higher = flags more photos as probably-deletable (more false "
            "positives). Lower = only the most obvious ones."
        )
        self.sensitivity.valueChanged.connect(self._repopulate)
        select_all = QPushButton("Check all")
        select_none = QPushButton("Uncheck all")
        select_all.clicked.connect(lambda: self.grid.set_all_checked(True))
        select_none.clicked.connect(lambda: self.grid.set_all_checked(False))
        self.ocr_btn = QPushButton("Refine with text detection")
        self.ocr_btn.setToolTip(
            "Run offline OCR on the shown candidates to confirm which actually "
            "contain text (messages/memes) and drop likely false positives."
        )
        self.ocr_btn.clicked.connect(self.ocr_requested)

        top = QHBoxLayout()
        top.addWidget(self._summary, 1)
        top.addWidget(self.sensitivity)
        top.addWidget(self.ocr_btn)
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

        note = QLabel(
            "Heuristic suggestions (screenshots, memes, saved images) — always "
            "review before deleting. Items copy to quarantine first if enabled."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #b3a9cc;")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.grid, 1)
        layout.addWidget(note)
        layout.addWidget(self.progress)
        layout.addLayout(bottom)

        self.grid.selection_changed.connect(self._update_summary)

    def set_thumb_cache(self, cache: dict[str, QImage]) -> None:
        self._thumb_cache = cache

    def set_items(self, items: list[MediaItem]) -> None:
        self._all_items = items
        self._repopulate()

    def set_busy(self, busy: bool) -> None:
        self.progress.setVisible(busy)
        self.delete_btn.setEnabled(not busy and bool(self.grid.checked_items()))

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    # -- internals --------------------------------------------------------
    def _repopulate(self) -> None:
        threshold = self.sensitivity.value() / 100.0
        scored = []
        for it in self._all_items:
            if it.is_live_motion:
                continue
            score, reasons = ephemeral_score(it)
            if score >= threshold and reasons:
                scored.append((score, reasons, it))
        scored.sort(key=lambda t: t[0], reverse=True)

        self.grid.clear_items()
        self.grid.add_items([it for _s, _r, it in scored], checked=True)
        for _score, reasons, it in scored:
            cached = self._thumb_cache.get(it.afc_path)
            if cached is not None:
                self.grid.set_thumbnail(it.afc_path, cached)
            item = self.grid._by_path.get(it.afc_path)
            if item is not None:
                item.setToolTip(item.toolTip() + "\nLikely: " + ", ".join(reasons))
        self._update_summary()

    def _update_summary(self) -> None:
        checked = self.grid.checked_items()
        shown = self.grid.count()
        mb = sum(m.size for m in checked) / (1024 * 1024)
        self._summary.setText(
            f"{shown} likely-deletable · {len(checked)} checked · {mb:.0f} MB"
        )
        self.delete_btn.setEnabled(bool(checked))
