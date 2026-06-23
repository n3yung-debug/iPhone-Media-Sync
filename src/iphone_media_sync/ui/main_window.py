"""Main application window: device detection + the three workflow tabs."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QThread
from PySide6.QtGui import QImage
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)

from ..core.backup import BackupResult
from ..core.config import Config
from ..core.dedupe import find_exact_duplicates, find_similar_images
from ..core.index import BackupIndex
from ..device.detector import DeviceDetector
from ..device.models import DeviceInfo, MediaItem
from .backup_tab import BackupTab
from .cleanup_tab import CleanupTab
from .duplicates_tab import DuplicatesTab
from .settings_dialog import SettingsDialog
from .workers import AnalyzeWorker, BackupWorker, DeleteWorker, ScanWorker

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iPhone Media Sync")
        self.resize(1100, 760)

        self.config = Config.load()
        self.index = BackupIndex()

        self.udid: Optional[str] = None
        self.items: list[MediaItem] = []
        self.thumb_cache: dict[str, QImage] = {}
        self._threads: dict[str, tuple[QThread, object]] = {}

        # Tabs
        self.backup_tab = BackupTab()
        self.duplicates_tab = DuplicatesTab(threshold=self.config.perceptual_threshold)
        self.cleanup_tab = CleanupTab(require_backup=self.config.require_backup_before_delete)
        self.duplicates_tab.set_thumb_cache(self.thumb_cache)

        self.tabs = QTabWidget()
        self.tabs.addTab(self.backup_tab, "Backup")
        self.tabs.addTab(self.duplicates_tab, "Duplicates")
        self.tabs.addTab(self.cleanup_tab, "Free up space")
        self.setCentralWidget(self.tabs)

        self._build_toolbar()
        self.setStatusBar(QStatusBar())
        self._set_device_status("No device. Plug in an iPhone and unlock it.")

        self._wire_signals()

        # Device detection
        self.detector = DeviceDetector()
        self.detector.device_connected.connect(self._on_device_connected)
        self.detector.device_disconnected.connect(self._on_device_disconnected)
        self.detector.start()

    # -- setup ------------------------------------------------------------
    def _build_toolbar(self) -> None:
        bar = QToolBar()
        bar.setMovable(False)
        self.addToolBar(bar)
        self._device_label = QLabel("  No device  ")
        bar.addWidget(self._device_label)
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().horizontalPolicy().Expanding,  # type: ignore[attr-defined]
                             spacer.sizePolicy().verticalPolicy())
        bar.addWidget(spacer)
        settings_btn = QPushButton("Settings…")
        settings_btn.clicked.connect(self._open_settings)
        bar.addWidget(settings_btn)

    def _wire_signals(self) -> None:
        self.backup_tab.backup_clicked.connect(self._start_backup)
        self.backup_tab.cancel_clicked.connect(self._cancel_backup)
        self.duplicates_tab.find_clicked.connect(self._find_duplicates)
        self.duplicates_tab.exclude_clicked.connect(self._exclude_from_backup)
        self.duplicates_tab.delete_clicked.connect(self._delete_items)
        self.cleanup_tab.delete_clicked.connect(self._delete_from_cleanup)

    # -- device events ----------------------------------------------------
    def _on_device_connected(self, info: DeviceInfo) -> None:
        if self.udid == info.udid:
            return
        self.udid = info.udid
        self._set_device_status(f"Connected: {info}")
        self._device_label.setText(f"  📱 {info.name}  ")
        self.backup_tab.set_summary("Scanning camera roll…")
        self._start_scan()

    def _on_device_disconnected(self, udid: str) -> None:
        if udid != self.udid:
            return
        self.udid = None
        self.items = []
        self.thumb_cache.clear()
        self._device_label.setText("  No device  ")
        self._set_device_status("Device disconnected.")
        self.backup_tab.grid.clear_items()
        self.backup_tab.set_summary("Connect an iPhone to begin.")
        self.backup_tab.set_ready(False)
        self.cleanup_tab.grid.clear_items()

    # -- scan + analyze ---------------------------------------------------
    def _start_scan(self) -> None:
        if not self.udid:
            return
        worker = ScanWorker(self.udid)
        worker.finished.connect(self._on_scan_done)
        worker.error.connect(self._on_worker_error)
        self._run("scan", worker)

    def _on_scan_done(self, items: list[MediaItem]) -> None:
        self.items = items
        self.thumb_cache.clear()
        self.backup_tab.grid.clear_items()
        self.backup_tab.grid.add_items(items, checked=True)
        self.cleanup_tab.populate(items)
        self.backup_tab.set_ready(True)
        photos = sum(1 for it in items if it.kind.value == "photo")
        videos = sum(1 for it in items if it.kind.value == "video")
        self._set_device_status(
            f"Found {len(items)} items ({photos} photos, {videos} videos). "
            "Analyzing for thumbnails and duplicates…"
        )
        self._start_analyze()

    def _start_analyze(self) -> None:
        if not self.udid:
            return
        worker = AnalyzeWorker(
            self.udid, self.items, self.index,
            want_perceptual=self.config.detect_perceptual,
        )
        worker.thumb_ready.connect(self._on_thumb_ready)
        worker.item_analyzed.connect(self._on_item_analyzed)
        worker.progress.connect(self._on_analyze_progress)
        worker.finished.connect(self._on_analyze_done)
        worker.error.connect(self._on_worker_error)
        self._run("analyze", worker)

    def _on_thumb_ready(self, afc_path: str, image: QImage) -> None:
        self.thumb_cache[afc_path] = image
        self.backup_tab.grid.set_thumbnail(afc_path, image)
        self.cleanup_tab.grid.set_thumbnail(afc_path, image)

    def _on_item_analyzed(self, item: MediaItem) -> None:
        self.backup_tab.grid.refresh_label(item)
        self.cleanup_tab.grid.refresh_label(item)

    def _on_analyze_progress(self, done: int, total: int) -> None:
        self._set_device_status(f"Analyzing {done}/{total}…")

    def _on_analyze_done(self) -> None:
        self.cleanup_tab._apply_filter()
        self._set_device_status("Ready. Review and back up, or check the Duplicates tab.")

    # -- backup -----------------------------------------------------------
    def _start_backup(self) -> None:
        if not self.udid:
            return
        if not self.config.backup_targets:
            QMessageBox.information(
                self, "Choose a destination",
                "Pick at least one backup folder in Settings first.",
            )
            self._open_settings()
            if not self.config.backup_targets:
                return
        selected = self.backup_tab.grid.checked_items()
        if not selected:
            QMessageBox.information(self, "Nothing selected",
                                    "Check at least one item to back up.")
            return

        self.backup_tab.set_busy(True)
        self.backup_tab.progress.setRange(0, len(selected))
        worker = BackupWorker(self.config, self.index, self.udid, selected)
        worker.progress.connect(self._on_backup_progress)
        worker.message.connect(self.backup_tab.set_status)
        worker.finished.connect(self._on_backup_done)
        worker.error.connect(self._on_backup_error)
        self._backup_worker = worker
        self._run("backup", worker)

    def _cancel_backup(self) -> None:
        worker = getattr(self, "_backup_worker", None)
        if worker is not None:
            worker.cancel()
            self.backup_tab.set_status("Cancelling…")

    def _on_backup_progress(self, done: int, total: int, name: str) -> None:
        self.backup_tab.progress.setValue(done)
        self.backup_tab.set_status(f"Backing up {done}/{total}: {name}")

    def _on_backup_done(self, result: BackupResult) -> None:
        self.backup_tab.set_busy(False)
        for it in self.items:
            self.backup_tab.grid.refresh_label(it)
            self.cleanup_tab.grid.refresh_label(it)
        self.cleanup_tab._apply_filter()
        msg = (
            f"Backed up {result.copied} item(s), "
            f"{result.bytes_copied / (1024*1024):.0f} MB. "
            f"Skipped {result.skipped_existing} already-backed-up."
        )
        if result.failed:
            msg += f" {result.failed} failed."
        self.backup_tab.set_status(msg)
        self._set_device_status(msg)
        if result.errors:
            QMessageBox.warning(self, "Some items failed",
                                "\n".join(result.errors[:20]))

    def _on_backup_error(self, message: str) -> None:
        self.backup_tab.set_busy(False)
        QMessageBox.critical(self, "Backup failed", message)

    # -- duplicates -------------------------------------------------------
    def _find_duplicates(self, threshold: int) -> None:
        groups = []
        if self.config.detect_exact:
            groups.extend(find_exact_duplicates(self.items))
        if self.config.detect_perceptual:
            groups.extend(find_similar_images(self.items, threshold=threshold))
        self.duplicates_tab.set_thumb_cache(self.thumb_cache)
        self.duplicates_tab.show_groups(groups)

    def _exclude_from_backup(self, items: list[MediaItem]) -> None:
        for it in items:
            self.backup_tab.grid.set_checked(it.afc_path, False)
        QMessageBox.information(
            self, "Excluded",
            f"{len(items)} duplicate copy(ies) unchecked on the Backup tab.",
        )
        self.tabs.setCurrentWidget(self.backup_tab)

    # -- deletion ---------------------------------------------------------
    def _delete_from_cleanup(self) -> None:
        self._delete_items(self.cleanup_tab.grid.checked_items())

    def _delete_items(self, items: list[MediaItem]) -> None:
        if not self.udid or not items:
            return
        not_backed = [it for it in items if not it.backed_up]
        if self.config.require_backup_before_delete and not_backed:
            QMessageBox.warning(
                self, "Not backed up",
                f"{len(not_backed)} of these are not verified-backed-up yet. "
                "Back them up first, or turn off the safety check in Settings.",
            )
            return

        mb = sum(it.size for it in items) / (1024 * 1024)
        confirm = QMessageBox.question(
            self, "Delete from phone?",
            f"Permanently delete {len(items)} item(s) ({mb:.0f} MB) from the iPhone?\n\n"
            "This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        worker = DeleteWorker(self.udid, items)
        worker.finished.connect(self._on_delete_done)
        worker.error.connect(self._on_worker_error)
        self.cleanup_tab.set_busy(True)
        self._run("delete", worker)

    def _on_delete_done(self, deleted: int, errors: list) -> None:
        self.cleanup_tab.set_busy(False)
        # Drop deleted items from the in-memory model and grids.
        gone = {it.afc_path for it in self.cleanup_tab.grid.checked_items()}
        self.items = [it for it in self.items if it.afc_path not in gone]
        self.cleanup_tab.grid.remove_paths(gone)
        self.backup_tab.grid.remove_paths(gone)
        msg = f"Deleted {deleted} item(s) from the phone."
        if errors:
            msg += f" {len(errors)} failed."
            QMessageBox.warning(self, "Some deletions failed", "\n".join(errors[:20]))
        self._set_device_status(msg)

    # -- misc -------------------------------------------------------------
    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self.config = dlg.result_config()
            self.config.save()
            self.cleanup_tab._require_backup = self.config.require_backup_before_delete

    def _on_worker_error(self, message: str) -> None:
        self._set_device_status(message)
        QMessageBox.warning(self, "Device error", message)

    def _set_device_status(self, text: str) -> None:
        self.statusBar().showMessage(text)

    # -- thread plumbing --------------------------------------------------
    def _run(self, name: str, worker) -> None:
        """Run ``worker.run`` on a dedicated QThread and keep it alive."""
        prev = self._threads.get(name)
        if prev is not None:
            old_thread, _ = prev
            if old_thread.isRunning():
                old_thread.quit()
                old_thread.wait(2000)

        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)

        def cleanup():
            thread.quit()
            thread.wait(2000)

        for sig_name in ("finished", "error"):
            sig = getattr(worker, sig_name, None)
            if sig is not None:
                sig.connect(cleanup)

        self._threads[name] = (thread, worker)
        thread.start()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        self.detector.stop()
        for thread, _ in self._threads.values():
            thread.quit()
            thread.wait(2000)
        self.index.close()
        super().closeEvent(event)
