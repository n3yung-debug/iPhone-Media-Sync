"""A reusable filter/search/sort bar that yields a predicate over MediaItems."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..device.models import MediaItem, MediaKind

_TYPE_ALL = "All types"
_TYPE_PHOTOS = "Photos"
_TYPE_VIDEOS = "Videos"
_TYPE_SHOTS = "Screenshots"

# Sort options: label -> (key function, reverse)
_SORTS: dict[str, tuple] = {
    "Newest first": (lambda m: m.best_date or datetime.min, True),
    "Oldest first": (lambda m: m.best_date or datetime.max, False),
    "Largest first": (lambda m: m.size or 0, True),
    "Smallest first": (lambda m: m.size or 0, False),
    "Name (A–Z)": (lambda m: m.filename.lower(), False),
}

_DATE_ANY = "Any date"
_DATE_BEFORE = "Before"
_DATE_AFTER = "After"


class FilterBar(QWidget):
    """Search + media-type + min-size + date + sort. Emits ``changed``."""

    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search filename…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.changed)

        self.kind = QComboBox()
        self.kind.addItems([_TYPE_ALL, _TYPE_PHOTOS, _TYPE_VIDEOS, _TYPE_SHOTS])
        self.kind.currentIndexChanged.connect(self.changed)

        self.min_mb = QSpinBox()
        self.min_mb.setRange(0, 100000)
        self.min_mb.setSuffix(" MB+")
        self.min_mb.setToolTip("Only show items at least this large.")
        self.min_mb.valueChanged.connect(self.changed)

        self.date_mode = QComboBox()
        self.date_mode.addItems([_DATE_ANY, _DATE_BEFORE, _DATE_AFTER])
        self.date_mode.currentIndexChanged.connect(self._on_date_mode)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate(2023, 1, 1))
        self.date_edit.setEnabled(False)
        self.date_edit.dateChanged.connect(self.changed)

        self.sort = QComboBox()
        self.sort.addItems(list(_SORTS.keys()))
        self.sort.currentIndexChanged.connect(self.changed)

        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.addWidget(QLabel("Filter:"))
        row1.addWidget(self.search, 1)
        row1.addWidget(self.kind)
        row1.addWidget(self.min_mb)

        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.addWidget(QLabel("Date:"))
        row2.addWidget(self.date_mode)
        row2.addWidget(self.date_edit)
        row2.addStretch(1)
        row2.addWidget(QLabel("Sort:"))
        row2.addWidget(self.sort)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row1)
        layout.addLayout(row2)

    def _on_date_mode(self) -> None:
        self.date_edit.setEnabled(self.date_mode.currentText() != _DATE_ANY)
        self.changed.emit()

    # -- sorting ----------------------------------------------------------
    def sort_key(self):
        return _SORTS[self.sort.currentText()][0]

    def sort_reverse(self) -> bool:
        return _SORTS[self.sort.currentText()][1]

    # -- filtering --------------------------------------------------------
    def matches(self, media: MediaItem) -> bool:
        text = self.search.text().strip().lower()
        if text and text not in media.filename.lower():
            return False

        choice = self.kind.currentText()
        if choice == _TYPE_PHOTOS and media.kind != MediaKind.PHOTO:
            return False
        if choice == _TYPE_VIDEOS and media.kind != MediaKind.VIDEO:
            return False
        if choice == _TYPE_SHOTS and not media.is_screenshot:
            return False

        min_bytes = self.min_mb.value() * 1024 * 1024
        if min_bytes and (media.size or 0) < min_bytes:
            return False

        mode = self.date_mode.currentText()
        if mode != _DATE_ANY:
            limit = self.date_edit.date().toPython()  # datetime.date
            when = media.best_date
            if when is None:
                return False
            d = when.date()
            if mode == _DATE_BEFORE and not d < limit:
                return False
            if mode == _DATE_AFTER and not d > limit:
                return False
        return True
