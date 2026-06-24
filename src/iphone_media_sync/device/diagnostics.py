"""Self-diagnostics: report exactly why device detection might be failing.

Returns a plain-text report (with full tracebacks) so a user running the
packaged app can see the real error instead of a silent "No device".
"""

from __future__ import annotations

import platform
import sys
import traceback


def run_diagnostics() -> str:
    lines: list[str] = []

    def add(msg: str = "") -> None:
        lines.append(msg)

    add("=== iPhone Media Sync diagnostics ===")
    add(f"Platform: {platform.platform()}")
    add(f"Python: {sys.version.split()[0]}")
    add(f"Frozen (packaged exe): {getattr(sys, 'frozen', False)}")
    add("")

    # 1. Can we import pymobiledevice3 at all?
    try:
        import pymobiledevice3

        ver = getattr(pymobiledevice3, "__version__", "unknown")
        add(f"[OK] pymobiledevice3 imported (version {ver})")
    except Exception:  # noqa: BLE001
        add("[FAIL] Could not import pymobiledevice3:")
        add(traceback.format_exc())
        add("\n-> The device library isn't bundled/working. This is a packaging bug.")
        return "\n".join(lines)

    # 2. Can we import the usbmux entry point?
    try:
        from pymobiledevice3.usbmux import list_devices
        add("[OK] pymobiledevice3.usbmux.list_devices imported")
    except Exception:  # noqa: BLE001
        add("[FAIL] Could not import usbmux.list_devices:")
        add(traceback.format_exc())
        return "\n".join(lines)

    # 3. Can we actually reach usbmuxd (Apple Mobile Device Service) and list?
    try:
        devices = list_devices()
        add(f"[OK] usbmuxd reachable. Devices found: {len(devices)}")
        for d in devices:
            serial = getattr(d, "serial", None) or getattr(d, "udid", "?")
            conn = getattr(d, "connection_type", "?")
            add(f"     - serial={serial} connection_type={conn}")
        if not devices:
            add("\n-> usbmuxd is running but reports NO devices. Make sure the")
            add("   iPhone is unlocked and you've tapped 'Trust This Computer'.")
    except Exception:  # noqa: BLE001
        add("[FAIL] list_devices() raised (can't reach Apple Mobile Device Service):")
        add(traceback.format_exc())
        add("\n-> Apple Mobile Device Service may not be reachable on port 27015.")
        return "\n".join(lines)

    # 4. Try a lockdown handshake with the first device.
    if devices:
        try:
            from pymobiledevice3.lockdown import create_using_usbmux

            serial = getattr(devices[0], "serial", None)
            lockdown = create_using_usbmux(serial=serial)
            name = lockdown.get_value(key="DeviceName")
            add(f"[OK] Paired with device: {name}")
            try:
                lockdown.close()
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            add("[WARN] Found the device but couldn't pair (trust prompt?):")
            add(traceback.format_exc())

    return "\n".join(lines)
