"""Browse the quarantine folder: restore files, delete them, or empty it.

Quarantined files are local copies made before deleting from the phone, so this
makes deletion fully reversible.
"""

from __future__ import annotations

import io
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..core import quarantine
from ..core.storage import human_bytes

_ROLE_PATH = Qt.ItemDataRole.UserRole
_IMAGE_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".gif", ".tiff", ".webp", ".dng"}
_TILE = 160


class QuarantineDialog(QDialog):
    def __init__(self, quarantine_base: str, parent=None):
        super().__init__(parent)
        self._base = quarantine_base
        self.setWindowTitle("Quarantine")
        self.resize(820, 600)

        self._summary = QLabel("")
        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setIconSize(QSize(_TILE - 20, _TILE - 20))
        self._list.setGridSize(QSize(_TILE, _TILE + 16))
        self._list.setSpacing(6)
        self._list.setWordWrap(True)

        restore_btn = QPushButton("Restore checked to…")
        delete_btn = QPushButton("Delete checked permanently")
        empty_btn = QPushButton("Empty quarantine")
        open_btn = QPushButton("Open folder")
        close_btn = QPushButton("Close")
        restore_btn.clicked.connect(self._restore)
        delete_btn.clicked.connect(self._delete)
        empty_btn.clicked.connect(self._empty)
        open_btn.clicked.connect(self._open_folder)
        close_btn.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(open_btn)
        buttons.addStretch(1)
        buttons.addWidget(restore_btn)
        buttons.addWidget(delete_btn)
        buttons.addWidget(empty_btn)
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._summary)
        layout.addWidget(self._list, 1)
        layout.addLayout(buttons)

        self._reload()

    # -- data -------------------------------------------------------------
    def _reload(self) -> None:
        self._list.clear()
        files = quarantine.list_quarantined(self._base)
        for i, path in enumerate(files):
            item = QListWidgetItem(path.name)
            item.setData(_ROLE_PATH, str(path))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            # Decode a thumbnail for the first chunk to stay responsive.
            icon = _disk_thumbnail(path) if i < 300 else None
            item.setIcon(icon or _placeholder())
            try:
                item.setToolTip(f"{path}\n{human_bytes(path.stat().st_size)}")
            except OSError:
                item.setToolTip(str(path))
            self._list.addItem(item)
        total = human_bytes(quarantine.total_bytes(files))
        self._summary.setText(f"{len(files)} quarantined file(s) · {total}")

    def _checked_paths(self) -> list[Path]:
        out = []
        for i in range(self._list.count()):
            it = self._list.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(Path(it.data(_ROLE_PATH)))
        return out

    # -- actions ----------------------------------------------------------
    def _restore(self) -> None:
        paths = self._checked_paths()
        if not paths:
            QMessageBox.information(self, "Nothing checked", "Check files to restore.")
            return
        dest = QFileDialog.getExistingDirectory(self, "Restore to folder")
        if not dest:
            return
        restored = 0
        for p in paths:
            try:
                quarantine.restore_file(p, Path(dest))
                restored += 1
            except OSError as exc:
                QMessageBox.warning(self, "Restore failed", f"{p.name}: {exc}")
        QMessageBox.information(self, "Restored",
                                f"Restored {restored} file(s) to {dest}.")

    def _delete(self) -> None:
        paths = self._checked_paths()
        if not paths:
            QMessageBox.information(self, "Nothing checked", "Check files to delete.")
            return
        if QMessageBox.question(
            self, "Delete from quarantine?",
            f"Permanently delete {len(paths)} quarantined file(s) from disk?",
        ) == QMessageBox.StandardButton.Yes:
            quarantine.delete_files(paths)
            self._reload()

    def _empty(self) -> None:
        if QMessageBox.question(
            self, "Empty quarantine?",
            "Permanently delete ALL quarantined files from disk?",
        ) == QMessageBox.StandardButton.Yes:
            n = quarantine.empty_quarantine(self._base)
            self._reload()
            QMessageBox.information(self, "Emptied", f"Removed {n} file(s).")

    def _open_folder(self) -> None:
        base = quarantine.resolve_dir(self._base)
        base.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(base)))


def _placeholder() -> QPixmap:
    pm = QPixmap(_TILE - 20, _TILE - 20)
    pm.fill(QColor("#2f2649"))
    painter = QPainter(pm)
    painter.setPen(QColor("#b3a9cc"))
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "file")
    painter.end()
    return pm


def _disk_thumbnail(path: Path):
    if path.suffix.lower() not in _IMAGE_EXTS:
        return None
    try:
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
        except Exception:  # noqa: BLE001
            pass
        from PIL import Image

        with Image.open(path) as img:
            img = img.convert("RGBA")
            img.thumbnail((_TILE - 20, _TILE - 20))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
        qimg = QImage()
        qimg.loadFromData(buf.getvalue(), "PNG")
        return QPixmap.fromImage(qimg)
    except Exception:  # noqa: BLE001
        return None
