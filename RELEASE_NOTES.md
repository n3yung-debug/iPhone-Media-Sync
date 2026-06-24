# iPhone Media Sync v1.2.3

## Fix in 1.2.3 — detection (the real one)
- **Bundles the missing `win32security` (pywin32) module.** On Windows,
  `pymobiledevice3` 7.x imports `win32security` at runtime but doesn't declare
  `pywin32` as a dependency, so it was neither installed nor packaged — and
  device detection failed with `ModuleNotFoundError: No module named
  'win32security'`. The app now depends on `pywin32` and force-bundles it.
- Builds on v1.2.2, which pinned `pymobiledevice3` to its synchronous line.

If detection still fails, click **Diagnostics** and send the report. On Windows
you also need the classic **Apple Mobile Device Service** (desktop iTunes from
apple.com).

## Recent history
- **1.2.2** — pin `pymobiledevice3>=7.0.0,<8` (8.x+ went async).
- **1.2.1** — Diagnostics button + rotating log file.
- **1.2.0** — Windows installer, quarantine-on-delete, CI.
- **1.1.0** — Live Photos, EXIF dates, filters, best-of-burst, dry-run,
  resume/retry, scan cache, cleanup candidates, manifest, storage readouts,
  folder template, update checker, light theme.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.2.3.exe`
- **Portable:** `iPhoneMediaSync-windows.zip`

On first connection, unlock the iPhone and tap "Trust This Computer."
