# iPhone Media Sync v1.1.0

A big feature update on top of v1.0.0.

## New in 1.1.0
- **Live Photos** are paired (still + `.MOV`) and backed up / deleted together;
  the grid shows one tile per Live Photo with a ◉ badge.
- **EXIF capture-date foldering** — backups file under the date a photo was
  actually taken (falls back to the file's modified time).
- **Filter & search bar** — filter by filename, type (photo / video /
  screenshot), and minimum size, on the Backup and Free-up-space tabs.
- **Best-of-burst** — duplicate groups suggest keeping the sharpest frame.
- **Pre-backup dry-run** — see how much is new vs. already backed up, with a
  destination free-space warning, before copying.
- **Resume / retry** — failed items are tracked with a "Retry failed" button.
- **Faster re-scans** — a disk cache of hashes + thumbnails means re-plugging
  a phone skips re-reading unchanged files.
- **Cleanup candidates** — one-click select Screenshots, Blurry photos, or
  Large videos to review for deletion.
- **Backup manifest** — a CSV log of everything copied is written to each
  destination.
- **Storage readouts** for backup destinations.
- **Folder-template control** in Settings.
- **Update checker** — a toolbar link appears when a newer release exists.
- **Light theme** toggle alongside the dark purple theme.

## Core features (from 1.0.0)
- Auto-detect iPhone, back up to local/NAS folders, verify-after-copy,
  incremental backups, exact + perceptual duplicate review, and a
  review-and-mark "free up space" flow. Originals (HEIC/HEVC/MOV) untouched.

## Download
Grab `iPhoneMediaSync-windows.zip` below, unzip it anywhere, and run
`iPhoneMediaSync.exe`. On first connection, unlock the iPhone and tap
"Trust This Computer."
