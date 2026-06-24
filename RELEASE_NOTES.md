# iPhone Media Sync v1.2.2

## Fix in 1.2.2 — iPhone detection
- **Fixes the iPhone not being detected.** The `pymobiledevice3` dependency was
  unpinned, so builds pulled its 8.x/9.x release, which rewrote the API to be
  **async** — the app's synchronous calls silently returned un-awaited
  coroutines and no device was ever found. Pinned to the last synchronous line
  (`>=7.0.0,<8`), which matches the app's code.

If you're upgrading and still see "No device," click **Diagnostics** in the
toolbar and it should now report the device. On Windows you still need the
classic **Apple Mobile Device Service** (desktop iTunes from apple.com).

## From 1.2.1
- Diagnostics button and a rotating log file for troubleshooting detection.

## From 1.2.0
- Windows installer, quarantine-on-delete, and continuous integration.

## From 1.1.0
- Live Photos, EXIF capture-date foldering, filter & search, best-of-burst
  duplicate selection, pre-backup dry-run, resume/retry, faster re-scans,
  cleanup-candidate selectors, CSV manifest, storage readouts, folder template,
  update checker, and a light theme.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.2.2.exe`
- **Portable:** `iPhoneMediaSync-windows.zip`

On first connection, unlock the iPhone and tap "Trust This Computer."
