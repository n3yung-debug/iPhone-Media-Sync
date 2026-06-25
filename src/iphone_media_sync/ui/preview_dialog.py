"""A simple full-size image preview dialog (double-click a thumbnail)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout

from ..device.models import MediaItem


class PreviewDialog(QDialog):
    def __init__(self, media: MediaItem, parent=None):
        super().__init__(parent)
        self.setWindowTitle(media.filename)
        self.resize(900, 700)

        self._image_label = QLabel("Loading…")
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._image_label)

        mb = media.size / (1024 * 1024) if media.size else 0
        when = media.best_date.strftime("%Y-%m-%d %H:%M") if media.best_date else "unknown"
        dims = f"{media.width}×{media.height}  ·  " if media.width and media.height else ""
        self._info = QLabel(f"{dims}{mb:.1f} MB  ·  {when}  ·  {media.afc_path}")
        self._info.setWordWrap(True)
        self._info.setStyleSheet("color: #b3a9cc;")

        layout = QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._info)

    def set_image(self, image: QImage) -> None:
        self._image_label.setText("")
        self._image_label.setPixmap(QPixmap.fromImage(image))

    def set_error(self, message: str) -> None:
        self._image_label.setText(message)
