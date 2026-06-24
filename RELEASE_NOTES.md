# iPhone Media Sync v1.2.1

## New in 1.2.1
- **Diagnostics button** (toolbar) — reports exactly why the app can or can't
  see your iPhone (library load, Apple Mobile Device Service reachability,
  device list, and pairing), with full error detail you can copy.
- **Log file** — the app now writes a rotating log to
  `%USERPROFILE%\.iphone-media-sync\logs\app.log` so detection problems can be
  diagnosed after the fact.
- Detection failures are now recorded with the real underlying error instead of
  failing silently.

### Troubleshooting detection
On Windows, the app needs the classic **Apple Mobile Device Service** (installed
by the desktop **iTunes from apple.com** — *not* the Microsoft Store "iTunes"
or "Apple Devices" apps, which are sandboxed and don't install it). If the app
shows "No device" while Windows sees the phone, click **Diagnostics**.

## From 1.2.0
- Windows installer, quarantine-on-delete, and continuous integration.

## From 1.1.0
- Live Photos, EXIF capture-date foldering, filter & search, best-of-burst
  duplicate selection, pre-backup dry-run, resume/retry, faster re-scans,
  cleanup-candidate selectors, CSV manifest, storage readouts, folder template,
  update checker, and a light theme.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.2.1.exe`
- **Portable:** `iPhoneMediaSync-windows.zip`

On first connection, unlock the iPhone and tap "Trust This Computer."
