"""Detect iPhone plug-in / unplug events.

Polls usbmux for attached devices on a background thread and emits Qt signals
when a device appears or disappears. Polling (rather than usbmux's listen mode)
is deliberately simple and resilient to the daemon restarting.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from .afc_client import read_device_info
from .models import DeviceInfo

log = logging.getLogger(__name__)


_warned_import = False
_warned_list = False


def list_connected_udids() -> list[str]:
    """Return the UDIDs of all currently-attached devices (empty on error)."""
    global _warned_import, _warned_list
    try:
        from pymobiledevice3.usbmux import list_devices
    except Exception:  # noqa: BLE001 - import can fail in packaged builds
        if not _warned_import:
            log.warning("pymobiledevice3 could not be imported", exc_info=True)
            _warned_import = True
        return []
    try:
        devices = list_devices()
    except Exception:  # usbmuxd not running / unreachable
        if not _warned_list:
            log.warning("usbmux list_devices() failed", exc_info=True)
            _warned_list = True
        return []

    udids: list[str] = []
    for dev in devices:
        # Prefer USB connections; ignore network ("WiFi sync") pairings.
        conn = getattr(dev, "connection_type", "USB")
        if conn and conn.lower() != "usb":
            continue
        serial = getattr(dev, "serial", None) or getattr(dev, "udid", None)
        if serial:
            udids.append(serial)
    return udids


class DeviceDetector(QObject):
    """Emits signals as devices connect and disconnect.

    Signals:
        device_connected(DeviceInfo)
        device_disconnected(str)   # udid
    """

    device_connected = Signal(object)  # DeviceInfo
    device_disconnected = Signal(str)

    def __init__(self, poll_interval: float = 2.0, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._poll_interval = poll_interval
        self._thread = QThread()
        self._worker = _PollWorker(poll_interval)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.connected.connect(self.device_connected)
        self._worker.disconnected.connect(self.device_disconnected)

    def start(self) -> None:
        if not self._thread.isRunning():
            self._thread.start()

    def stop(self) -> None:
        self._worker.stop()
        self._thread.quit()
        self._thread.wait(3000)


class _PollWorker(QObject):
    connected = Signal(object)
    disconnected = Signal(str)

    def __init__(self, poll_interval: float):
        super().__init__()
        self._poll_interval = poll_interval
        self._running = True
        self._known: set[str] = set()

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        from PySide6.QtCore import QThread as _QT

        while self._running:
            current = set(list_connected_udids())

            for udid in current - self._known:
                try:
                    info = read_device_info(udid)
                except Exception as exc:  # not yet trusted / still booting
                    log.debug("device %s not ready: %s", udid, exc)
                    info = DeviceInfo(udid=udid)
                self.connected.emit(info)

            for udid in self._known - current:
                self.disconnected.emit(udid)

            self._known = current
            _QT.msleep(int(self._poll_interval * 1000))
