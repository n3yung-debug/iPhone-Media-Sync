"""A reusable filter/search bar that yields a predicate over MediaItems."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QWidget,
)

from ..device.models import MediaItem, MediaKind

_TYPE_ALL = "All types"
_TYPE_PHOTOS = "Photos"
_TYPE_VIDEOS = "Videos"
_TYPE_SHOTS = "Screenshots"


class FilterBar(QWidget):
    """Search box + media-type + minimum-size filter. Emits ``changed``."""

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

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Filter:"))
        layout.addWidget(self.search, 1)
        layout.addWidget(self.kind)
        layout.addWidget(self.min_mb)

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
        return True
