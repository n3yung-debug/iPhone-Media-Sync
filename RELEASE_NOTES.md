# iPhone Media Sync v1.2.4

## New in 1.2.4 — installer sets up Apple Mobile Device Support
- The installer now **detects whether Apple Mobile Device Support is installed**
  and, if it isn't, offers to **download Apple's official installer and run it**
  as part of setup — so you don't have to track it down separately.
- Apple's driver/service can't be legally bundled into this installer, so the
  bits are fetched from Apple (with your consent) at install time.

> If you decline, or you're offline, you can still install it later from
> https://www.apple.com/itunes/ (the desktop installer, not the Store version).

## Recent history
- **1.2.3** — bundle `pywin32` (`win32security`) so detection works on Windows.
- **1.2.2** — pin `pymobiledevice3>=7.0.0,<8` (8.x+ went async).
- **1.2.1** — Diagnostics button + rotating log file.
- **1.2.0** — Windows installer, quarantine-on-delete, CI.
- **1.1.0** — Live Photos, EXIF dates, filters, best-of-burst, dry-run,
  resume/retry, scan cache, cleanup candidates, manifest, storage readouts,
  folder template, update checker, light theme.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.2.4.exe`
- **Portable:** `iPhoneMediaSync-windows.zip`

On first connection, unlock the iPhone and tap "Trust This Computer."
