"""A scrollable, checkable thumbnail grid built on QListWidget (icon mode)."""

from __future__ import annotations


from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from ..device.models import MediaItem, MediaKind
from .theme import BG_RAISED, TEXT_MUTED

_TILE = 200
_ROLE_ITEM = Qt.ItemDataRole.UserRole


def _placeholder(kind: MediaKind) -> QPixmap:
    pm = QPixmap(_TILE - 24, _TILE - 24)
    pm.fill(QColor(BG_RAISED))
    painter = QPainter(pm)
    painter.setPen(QColor(TEXT_MUTED))
    label = "▶ video" if kind == MediaKind.VIDEO else "photo"
    painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, label)
    painter.end()
    return pm


class MediaGrid(QListWidget):
    """Grid of media tiles with per-item checkboxes.

    A checked tile means "selected for the current action" (back up, or delete).
    """

    selection_changed = Signal()
    item_activated = Signal(object)  # MediaItem (double-clicked)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemDoubleClicked.connect(
            lambda it: self.item_activated.emit(it.data(_ROLE_ITEM))
        )
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        # Allow ctrl/shift-click range selection (independent of check state).
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(_TILE - 24, _TILE - 24))
        self.setGridSize(QSize(_TILE, _TILE + 24))
        self.setSpacing(6)
        self.setWordWrap(True)
        self.setUniformItemSizes(False)
        self._by_path: dict[str, QListWidgetItem] = {}
        self.itemChanged.connect(lambda _i: self.selection_changed.emit())

    # -- population -------------------------------------------------------
    def clear_items(self) -> None:
        self.clear()
        self._by_path.clear()

    def add_item(self, media: MediaItem, checked: bool = True) -> None:
        item = QListWidgetItem(self._label_for(media))
        item.setData(_ROLE_ITEM, media)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        item.setIcon(_placeholder(media.kind))
        item.setToolTip(self._tooltip_for(media))
        self.addItem(item)
        self._by_path[media.afc_path] = item

    def add_items(self, items: list[MediaItem], checked: bool = True) -> None:
        for it in items:
            self.add_item(it, checked=checked)

    # -- thumbnails / badges ---------------------------------------------
    def set_thumbnail(self, afc_path: str, image: QImage) -> None:
        item = self._by_path.get(afc_path)
        if item is not None:
            item.setIcon(QPixmap.fromImage(image))

    def refresh_label(self, media: MediaItem) -> None:
        item = self._by_path.get(media.afc_path)
        if item is not None:
            item.setText(self._label_for(media))
            item.setToolTip(self._tooltip_for(media))

    # -- selection helpers ------------------------------------------------
    def set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.blockSignals(True)
        for i in range(self.count()):
            self.item(i).setCheckState(state)
        self.blockSignals(False)
        self.selection_changed.emit()

    def set_checked(self, afc_path: str, checked: bool) -> None:
        item = self._by_path.get(afc_path)
        if item is not None:
            state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            item.setCheckState(state)

    def remove_paths(self, paths: set[str]) -> None:
        for path in paths:
            item = self._by_path.pop(path, None)
            if item is not None:
                self.takeItem(self.row(item))

    def checked_items(self) -> list[MediaItem]:
        out = []
        for i in range(self.count()):
            it = self.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(_ROLE_ITEM))
        return out

    def all_items(self) -> list[MediaItem]:
        return [self.item(i).data(_ROLE_ITEM) for i in range(self.count())]

    # -- filtering --------------------------------------------------------
    def apply_filter(self, predicate) -> None:
        """Show only items for which ``predicate(media)`` is True (view only)."""
        for i in range(self.count()):
            it = self.item(i)
            it.setHidden(not predicate(it.data(_ROLE_ITEM)))

    def sort_by(self, key_func, reverse: bool = False) -> None:
        """Reorder tiles in place, preserving icons and check state."""
        items = []
        while self.count():
            items.append(self.takeItem(0))
        items.sort(key=lambda it: key_func(it.data(_ROLE_ITEM)), reverse=reverse)
        self.blockSignals(True)
        for it in items:
            self.addItem(it)
        self.blockSignals(False)

    def check_selected(self, checked: bool = True) -> None:
        """Check (or uncheck) the currently highlighted/selected tiles."""
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.blockSignals(True)
        for it in self.selectedItems():
            it.setCheckState(state)
        self.blockSignals(False)
        self.selection_changed.emit()

    def invert_checks(self) -> None:
        self.blockSignals(True)
        for i in range(self.count()):
            it = self.item(i)
            new = (Qt.CheckState.Unchecked if it.checkState() == Qt.CheckState.Checked
                   else Qt.CheckState.Checked)
            it.setCheckState(new)
        self.blockSignals(False)
        self.selection_changed.emit()

    def visible_checked_items(self) -> list[MediaItem]:
        out = []
        for i in range(self.count()):
            it = self.item(i)
            if not it.isHidden() and it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(_ROLE_ITEM))
        return out

    # -- formatting -------------------------------------------------------
    @staticmethod
    def _label_for(media: MediaItem) -> str:
        badges = ""
        if media.backed_up:
            badges += "✅"
        if media.has_live_motion:
            badges += "◉"
        if media.is_screenshot:
            badges += "▫"
        if badges:
            badges += " "
        return f"{badges}{media.filename}"

    @staticmethod
    def _tooltip_for(media: MediaItem) -> str:
        mb = media.size / (1024 * 1024) if media.size else 0
        when = media.best_date.strftime("%Y-%m-%d %H:%M") if media.best_date else "unknown"
        status = "already backed up" if media.backed_up else "not yet backed up"
        lines = [media.afc_path, f"{mb:.1f} MB · {when}", status]
        if media.width and media.height:
            lines.append(f"{media.width}×{media.height}")
        extras = []
        if media.has_live_motion:
            extras.append("Live Photo")
        if media.is_screenshot:
            extras.append("screenshot")
        if extras:
            lines.append(", ".join(extras))
        return "\n".join(lines)
