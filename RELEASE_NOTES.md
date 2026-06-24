# iPhone Media Sync v1.2.0

## New in 1.2.0
- **Windows installer** — releases now include `iPhoneMediaSync-Setup-<version>.exe`
  (Start-menu + optional desktop shortcuts, your app icon, and an uninstaller),
  alongside the portable `.zip`.
- **Quarantine-on-delete** — before anything is removed from the phone, each
  file is copied to a local quarantine folder, so a deletion is reversible. If
  the copy fails, the file is not deleted. On by default; the toggle and folder
  are in Settings.
- **Continuous integration** — tests and linting now run automatically on every
  change.

## From 1.1.0
- Live Photos paired (still + `.MOV`), EXIF capture-date foldering, filter &
  search, best-of-burst duplicate selection, pre-backup dry-run with free-space
  warning, resume/retry, faster re-scans via a disk cache, cleanup-candidate
  selectors (screenshots / blurry / large videos), CSV backup manifest, storage
  readouts, folder-template control, update checker, and a light theme.

## From 1.0.0
- Auto-detect iPhone, back up to local/NAS folders, verify-after-copy,
  incremental backups, exact + perceptual duplicate review, and a
  review-and-mark "free up space" flow. Originals (HEIC/HEVC/MOV) untouched.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.2.0.exe`
- **Portable:** `iPhoneMediaSync-windows.zip` — unzip and run `iPhoneMediaSync.exe`

On first connection, unlock the iPhone and tap "Trust This Computer."
