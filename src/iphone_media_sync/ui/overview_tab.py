"""Overview tab: at-a-glance stats about the connected library."""

from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ..core.classify import is_probably_deletable
from ..core.storage import human_bytes
from ..device.models import MediaItem, MediaKind


class OverviewTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._label = QLabel("Connect an iPhone and let analysis finish.")
        self._label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setWordWrap(True)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._label)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

    def set_items(self, items: list[MediaItem]) -> None:
        if not items:
            self._label.setText("Connect an iPhone and let analysis finish.")
            return
        self._label.setText(self._build_html(items))

    def _build_html(self, items: list[MediaItem]) -> str:
        photos = [it for it in items if it.kind == MediaKind.PHOTO]
        videos = [it for it in items if it.kind == MediaKind.VIDEO]
        live = sum(1 for it in items if it.has_live_motion)
        shots = sum(1 for it in items if it.is_screenshot)
        ephemeral = sum(1 for it in items if is_probably_deletable(it))
        total_bytes = sum(it.size or 0 for it in items)
        backed = [it for it in items if it.backed_up]
        backed_bytes = sum(it.size or 0 for it in backed)

        by_year: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # year -> [count, bytes]
        for it in items:
            year = it.best_date.strftime("%Y") if it.best_date else "unknown"
            by_year[year][0] += 1
            by_year[year][1] += it.size or 0

        largest = sorted(items, key=lambda it: it.size or 0, reverse=True)[:5]

        rows = "".join(
            f"<tr><td>{year}</td><td align='right'>{c}</td>"
            f"<td align='right'>{human_bytes(b)}</td></tr>"
            for year, (c, b) in sorted(by_year.items(), reverse=True)
        )
        big = "".join(
            f"<li>{it.filename} — {human_bytes(it.size)}</li>" for it in largest
        )
        pct_backed = (len(backed) / len(items) * 100) if items else 0

        return f"""
        <h2>Library overview</h2>
        <p><b>{len(items)}</b> items · <b>{human_bytes(total_bytes)}</b> total</p>
        <ul>
          <li>{len(photos)} photos, {len(videos)} videos</li>
          <li>{live} Live Photos · {shots} screenshots</li>
          <li>{ephemeral} flagged as probably-deletable</li>
        </ul>
        <h3>Backup status</h3>
        <p>{len(backed)} of {len(items)} backed up ({pct_backed:.0f}%) ·
           {human_bytes(backed_bytes)} secured ·
           {human_bytes(total_bytes - backed_bytes)} not yet backed up</p>
        <h3>By year</h3>
        <table cellpadding='4'>
          <tr><th align='left'>Year</th><th>Items</th><th>Size</th></tr>
          {rows}
        </table>
        <h3>Largest items</h3>
        <ul>{big}</ul>
        """
