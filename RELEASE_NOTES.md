# iPhone Media Sync v1.0.0

First release.

## Features
- **Auto-detect** iPhone plug-in / unplug (no Apple drivers required).
- **Backup** the camera roll to one or more local/NAS folders, organized into
  `YYYY/YYYY-MM-DD/`. Originals (HEIC / HEVC / MOV) are kept untouched.
- **Verify-after-copy** — every file is hash-checked at the destination before
  it counts as backed up.
- **Incremental** — a local index remembers what's already backed up, so
  re-plugging only copies new media.
- **Duplicate review** — groups exact (SHA-256) and visually-similar
  (perceptual hash) photos and suggests one to keep per group.
- **Free up space** — review what's on the phone and mark items for deletion;
  nothing is ever deleted automatically.
- **Purple-themed** PySide6 UI with a scrollable thumbnail grid.
- Version shown in the window title and toolbar; optional custom app icon.

## Download
Grab `iPhoneMediaSync-windows.zip` below, unzip it anywhere, and run
`iPhoneMediaSync.exe`. On first connection, unlock the iPhone and tap
"Trust This Computer."
