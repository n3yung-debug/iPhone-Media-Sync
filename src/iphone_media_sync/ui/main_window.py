"""Main application window: device detection + the three workflow tabs."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QThread
from PySide6.QtGui import QIcon, QImage
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)

from .. import __version__
from ..core.backup import BackupResult
from ..core.config import Config
from ..core.dedupe import find_exact_duplicates, find_similar_images
from ..core.estimate import estimate_backup
from ..core.index import BackupIndex
from ..core.live_photos import expand_with_live_partners, pair_live_photos
from ..core.quarantine import resolve_dir
from ..core.scan_cache import ScanCache
from ..core.storage import free_bytes, human_bytes
from ..device.detector import DeviceDetector
from ..device.models import DeviceInfo, MediaItem
from .backup_tab import BackupTab
from .cleanup_tab import CleanupTab
from .duplicates_tab import DuplicatesTab
from .resources import APP_ICON
from .settings_dialog import SettingsDialog
from .theme import apply_theme
from .workers import (
    AnalyzeWorker,
    BackupWorker,
    DeleteWorker,
    ScanWorker,
    UpdateCheckWorker,
)

log = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"iPhone Media Sync v{__version__}")
        if APP_ICON.exists():
            self.setWindowIcon(QIcon(str(APP_ICON)))
        self.resize(1100, 760)

        self.config = Config.load()
        self.index = BackupIndex()
        self.cache = ScanCache()

        self.udid: Optional[str] = None
        self.items: list[MediaItem] = []
        self._by_path: dict[str, MediaItem] = {}
        self.thumb_cache: dict[str, QImage] = {}
        self._threads: dict[str, tuple[QThread, object]] = {}
        self._last_failed: list[MediaItem] = []

        # Tabs
        self.backup_tab = BackupTab()
        self.duplicates_tab = DuplicatesTab(threshold=self.config.perceptual_threshold)
        self.cleanup_tab = CleanupTab(
            require_backup=self.config.require_backup_before_delete,
            blurry_threshold=self.config.blurry_threshold,
            large_video_mb=self.config.large_video_mb,
        )
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

        if self.config.check_updates:
            self._start_update_check()

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
        self._update_label = QLabel("")
        self._update_label.setOpenExternalLinks(True)
        self._update_label.setVisible(False)
        bar.addWidget(self._update_label)
        version_label = QLabel(f"v{__version__}  ")
        version_label.setStyleSheet("color: #b3a9cc;")
        bar.addWidget(version_label)
        settings_btn = QPushButton("Settings…")
        settings_btn.clicked.connect(self._open_settings)
        bar.addWidget(settings_btn)

    def _wire_signals(self) -> None:
        self.backup_tab.backup_clicked.connect(self._start_backup)
        self.backup_tab.cancel_clicked.connect(self._cancel_backup)
        self.backup_tab.retry_clicked.connect(self._retry_failed)
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
        self._by_path = {}
        self.thumb_cache.clear()
        self._device_label.setText("  No device  ")
        self._set_device_status("Device disconnected.")
        self.backup_tab.grid.clear_items()
        self.backup_tab.set_summary("Connect an iPhone to begin.")
        self.backup_tab.set_ready(False)
        self.cleanup_tab.grid.clear_items()

    # -- scan + analyze ---------------------------------------------------
    def _grid_items(self) -> list[MediaItem]:
        """Items shown in grids: hide Live Photo motion components."""
        return [it for it in self.items if not it.is_live_motion]

    def _start_scan(self) -> None:
        if not self.udid:
            return
        worker = ScanWorker(self.udid)
        worker.finished.connect(self._on_scan_done)
        worker.error.connect(self._on_worker_error)
        self._run("scan", worker)

    def _on_scan_done(self, items: list[MediaItem]) -> None:
        pair_live_photos(items)
        self.items = items
        self._by_path = {it.afc_path: it for it in items}
        self.thumb_cache.clear()
        grid_items = self._grid_items()
        self.backup_tab.grid.clear_items()
        self.backup_tab.grid.add_items(grid_items, checked=True)
        self.cleanup_tab.populate(grid_items)
        self.backup_tab.set_ready(True)
        photos = sum(1 for it in items if it.kind.value == "photo")
        videos = sum(1 for it in items if it.kind.value == "video")
        lives = sum(1 for it in items if it.has_live_motion)
        self._set_device_status(
            f"Found {len(items)} items ({photos} photos, {videos} videos, "
            f"{lives} Live Photos). Analyzing…"
        )
        self._start_analyze()

    def _start_analyze(self) -> None:
        if not self.udid:
            return
        worker = AnalyzeWorker(
            self.udid, self.items, self.index, self.cache,
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
        self.backup_tab._refilter()
        self._set_device_status(
            "Ready. Review and back up, or check the Duplicates tab. "
            + self._storage_summary()
        )

    # -- backup -----------------------------------------------------------
    def _start_backup(self) -> None:
        selected = self.backup_tab.grid.checked_items()
        if not self._ensure_target():
            return
        if not selected:
            QMessageBox.information(self, "Nothing selected",
                                    "Check at least one item to back up.")
            return
        self._run_backup(selected, confirm=True)

    def _retry_failed(self) -> None:
        if self._last_failed:
            self._run_backup(list(self._last_failed), confirm=False)

    def _ensure_target(self) -> bool:
        if self.config.backup_targets:
            return True
        QMessageBox.information(
            self, "Choose a destination",
            "Pick at least one backup folder in Settings first.",
        )
        self._open_settings()
        return bool(self.config.backup_targets)

    def _run_backup(self, selected: list[MediaItem], confirm: bool) -> None:
        if not self.udid:
            return
        # Keep Live Photo stills + their motion .MOV together.
        items = expand_with_live_partners(selected, self._by_path)
        est = estimate_backup(items)

        if confirm:
            if est.new == 0:
                QMessageBox.information(
                    self, "Nothing new",
                    "Everything selected is already backed up.",
                )
                return
            warning = self._storage_warning(est.bytes_new)
            proceed = QMessageBox.question(
                self, "Back up?",
                f"{est.summary()}\n\nDestinations: {len(self.config.backup_targets)}."
                f"{warning}\n\nProceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if proceed != QMessageBox.StandardButton.Yes:
                return

        self.backup_tab.set_busy(True)
        self.backup_tab.show_retry(0)
        self.backup_tab.progress.setRange(0, len(items))
        worker = BackupWorker(self.config, self.index, self.udid, items)
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
        self._last_failed = list(result.failed_items)
        self.backup_tab.show_retry(len(self._last_failed))
        msg = (
            f"Backed up {result.copied} item(s), "
            f"{result.bytes_copied / (1024*1024):.0f} MB. "
            f"Skipped {result.skipped_existing} already-backed-up."
        )
        if result.failed:
            msg += f" {result.failed} failed (use 'Retry failed')."
        if result.manifest_paths:
            msg += f" Manifest: {result.manifest_paths[0]}"
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
        # Deleting one half of a Live Photo removes both.
        items = expand_with_live_partners(items, self._by_path)
        not_backed = [it for it in items if not it.backed_up]
        if self.config.require_backup_before_delete and not_backed:
            QMessageBox.warning(
                self, "Not backed up",
                f"{len(not_backed)} of these are not verified-backed-up yet. "
                "Back them up first, or turn off the safety check in Settings.",
            )
            return

        mb = sum(it.size for it in items) / (1024 * 1024)
        if self.config.quarantine_before_delete:
            where = resolve_dir(self.config.quarantine_dir)
            safety = (
                f"\n\nA reversible copy will first be saved to:\n{where}"
            )
        else:
            safety = "\n\nThis cannot be undone."
        confirm = QMessageBox.question(
            self, "Delete from phone?",
            f"Delete {len(items)} item(s) ({mb:.0f} MB) from the iPhone?{safety}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        qdir = (
            (self.config.quarantine_dir or str(resolve_dir("")))
            if self.config.quarantine_before_delete
            else None
        )
        worker = DeleteWorker(self.udid, items, qdir)
        worker.finished.connect(self._on_delete_done)
        worker.error.connect(self._on_worker_error)
        self.cleanup_tab.set_busy(True)
        self._run("delete", worker)

    def _on_delete_done(self, deleted_paths: list, errors: list,
                        quarantine_dir: str) -> None:
        self.cleanup_tab.set_busy(False)
        gone = set(deleted_paths)
        self.items = [it for it in self.items if it.afc_path not in gone]
        self._by_path = {it.afc_path: it for it in self.items}
        self.cleanup_tab.grid.remove_paths(gone)
        self.backup_tab.grid.remove_paths(gone)
        msg = f"Deleted {len(gone)} item(s) from the phone."
        if quarantine_dir:
            msg += f" Copies saved to {quarantine_dir} (delete that folder to reclaim disk space)."
        if errors:
            msg += f" {len(errors)} not deleted."
            QMessageBox.warning(self, "Some items were not deleted",
                                "\n".join(errors[:20]))
        self._set_device_status(msg)

    # -- updates ----------------------------------------------------------
    def _start_update_check(self) -> None:
        worker = UpdateCheckWorker(__version__)
        worker.update_available.connect(self._on_update_available)
        self._run("update", worker)

    def _on_update_available(self, latest: str, url: str) -> None:
        self._update_label.setText(
            f'<a href="{url}" style="color:#b389ff;">Update {latest} available</a>  '
        )
        self._update_label.setVisible(True)

    # -- misc -------------------------------------------------------------
    def _storage_summary(self) -> str:
        parts = []
        for t in self.config.backup_targets:
            parts.append(f"{t}: {human_bytes(free_bytes(t))} free")
        return " · ".join(parts)

    def _storage_warning(self, need_bytes: int) -> str:
        frees = [free_bytes(t) for t in self.config.backup_targets]
        avail = [f for f in frees if f is not None]
        if avail and need_bytes > min(avail):
            return (
                f"\n\n⚠ This may not fit: needs {human_bytes(need_bytes)}, "
                f"smallest destination has {human_bytes(min(avail))} free."
            )
        return ""

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config, self)
        if dlg.exec():
            self.config = dlg.result_config()
            self.config.save()
            self.cleanup_tab.set_require_backup(self.config.require_backup_before_delete)
            self.cleanup_tab.set_thresholds(
                self.config.blurry_threshold, self.config.large_video_mb
            )
            app = QApplication.instance()
            if app is not None:
                apply_theme(app, self.config.theme)

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

        for sig_name in ("finished", "error", "update_available"):
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
        self.cache.close()
        super().closeEvent(event)
