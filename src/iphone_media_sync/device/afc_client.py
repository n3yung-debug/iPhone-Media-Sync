"""Read and delete iPhone media over AFC (Apple File Conduit).

Wraps ``pymobiledevice3`` so the rest of the app never imports it directly.
The AFC "media" service exposes the same DCIM tree the Photos app writes to,
which is exactly what we want to back up and (after review) delete.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterator, Optional

from .models import DeviceInfo, MediaItem, kind_for_path

log = logging.getLogger(__name__)

# Root of the camera roll within the AFC media partition.
DCIM_ROOT = "DCIM"


class DeviceError(RuntimeError):
    """Raised when the device can't be reached or AFC fails."""


def _require_pymobiledevice3():
    try:
        from pymobiledevice3.lockdown import create_using_usbmux  # noqa: F401
        from pymobiledevice3.services.afc import AfcService  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise DeviceError(
            "pymobiledevice3 is not installed. Run: pip install -r requirements.txt"
        ) from exc


def read_device_info(udid: Optional[str] = None) -> DeviceInfo:
    """Return identity info for a connected device (the first one if no udid)."""
    _require_pymobiledevice3()
    from pymobiledevice3.lockdown import create_using_usbmux

    try:
        lockdown = create_using_usbmux(serial=udid)
    except Exception as exc:  # pymobiledevice3 raises a variety of types
        raise DeviceError(f"Could not connect to device: {exc}") from exc

    def val(key: str, default: str = "") -> str:
        try:
            return str(lockdown.get_value(key=key) or default)
        except Exception:
            return default

    return DeviceInfo(
        udid=getattr(lockdown, "udid", "") or (udid or ""),
        name=val("DeviceName", "iPhone"),
        product_type=val("ProductType"),
        ios_version=val("ProductVersion"),
    )


class AfcMedia:
    """A live AFC session against one device's media partition.

    Use as a context manager so the underlying connection is always closed::

        with AfcMedia(udid) as media:
            for item in media.scan():
                ...
    """

    def __init__(self, udid: Optional[str] = None):
        _require_pymobiledevice3()
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.afc import AfcService

        try:
            self._lockdown = create_using_usbmux(serial=udid)
            self._afc = AfcService(lockdown=self._lockdown)
        except Exception as exc:
            raise DeviceError(
                "Could not open the media folder. Make sure the iPhone is "
                "unlocked and you've tapped 'Trust This Computer'."
            ) from exc

    # -- lifecycle --------------------------------------------------------
    def close(self) -> None:
        for obj in (self._afc, self._lockdown):
            try:
                obj.close()
            except Exception:  # pragma: no cover - best effort
                pass

    def __enter__(self) -> "AfcMedia":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- reading ----------------------------------------------------------
    def scan(self) -> Iterator[MediaItem]:
        """Yield every photo/video found under DCIM."""
        try:
            walker = self._afc.walk(DCIM_ROOT)
        except Exception as exc:
            raise DeviceError(f"Could not list DCIM: {exc}") from exc

        for dirpath, _dirs, files in walker:
            for name in files:
                path = f"{dirpath}/{name}".replace("//", "/")
                kind = kind_for_path(path)
                size, modified = self._stat(path)
                yield MediaItem(
                    afc_path=path,
                    size=size,
                    modified=modified,
                    kind=kind,
                )

    def _stat(self, path: str) -> tuple[int, Optional[datetime]]:
        try:
            st = self._afc.stat(path)
        except Exception:
            return 0, None
        size = int(st.get("st_size", 0) or 0)
        mtime = st.get("st_mtime")
        modified: Optional[datetime] = None
        if isinstance(mtime, datetime):
            modified = mtime
        elif isinstance(mtime, (int, float)):
            # AFC reports nanoseconds in some versions; normalise.
            ts = mtime / 1e9 if mtime > 1e12 else mtime
            try:
                modified = datetime.fromtimestamp(ts)
            except (OverflowError, OSError, ValueError):
                modified = None
        return size, modified

    def read_bytes(self, afc_path: str) -> bytes:
        """Return the full contents of a file on the device."""
        try:
            return self._afc.get_file_contents(afc_path)
        except Exception as exc:
            raise DeviceError(f"Could not read {afc_path}: {exc}") from exc

    def stream_to(self, afc_path: str, dest_path: str, chunk: int = 1 << 20) -> int:
        """Copy a device file to ``dest_path`` on disk; return bytes written.

        Uses chunked reads so large videos don't have to fit in memory.
        """
        written = 0
        try:
            handle = self._afc.fopen(afc_path, "r")
        except Exception:
            # Older API without fopen: fall back to a full read.
            data = self.read_bytes(afc_path)
            with open(dest_path, "wb") as fh:
                fh.write(data)
            return len(data)

        try:
            with open(dest_path, "wb") as fh:
                while True:
                    block = self._afc.fread(handle, chunk)
                    if not block:
                        break
                    fh.write(block)
                    written += len(block)
        finally:
            try:
                self._afc.fclose(handle)
            except Exception:  # pragma: no cover - best effort
                pass
        return written

    # -- deleting ---------------------------------------------------------
    def delete(self, afc_path: str) -> None:
        """Remove a single file from the device. Caller must confirm first."""
        try:
            self._afc.rm(afc_path)
        except Exception as exc:
            raise DeviceError(f"Could not delete {afc_path}: {exc}") from exc
