# iPhone Media Sync

A Windows desktop app that detects when an iPhone is plugged in, backs up its
photos and videos to a local folder or NAS, finds duplicates so you don't waste
space, and lets you review-and-delete media from the phone to free it up.

**Nothing is ever deleted automatically.** Anything the app thinks is a
duplicate or removable is shown in a review grid where you mark each item
**Keep** or **Delete** and confirm before anything leaves your phone.

## Features

- **Auto-detect** iPhone plug-in / unplug (no Apple drivers required).
- **Backup tab** — scrollable thumbnail grid of the camera roll; everything is
  selected by default, uncheck anything you don't want. Copies originals
  (HEIC / HEVC / MOV untouched) into `YYYY/YYYY-MM-DD/` folders.
- **Verify-after-copy** — every file is hash-checked at the destination before
  it counts as backed up.
- **Incremental** — a local index remembers what's already backed up (by hash),
  so re-plugging only copies new media.
- **Duplicates tab** — groups exact (SHA-256) and visually-similar (perceptual
  hash, configurable threshold) photos; suggests one to keep per group.
- **Free-up-space tab** — review what's on the phone and mark items for
  deletion; only verified-backed-up items can be marked by default.

## Requirements

- Windows 10/11
- Python 3.10+
- iTunes / Apple Mobile Device Support **not strictly required** —
  `pymobiledevice3` talks to the device directly — but having the Apple USB
  driver installed makes detection more reliable on some machines.
- The first time you connect, **unlock the iPhone and tap "Trust This
  Computer."**

## Install

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bat
python -m iphone_media_sync
```

(Run from the `src/` directory, or install the package with `pip install -e .`)

## Build a standalone app (no Python needed to run)

The build produces a **folder** (`dist\iPhoneMediaSync\`) with
`iPhoneMediaSync.exe` inside. A folder build launches fast because nothing has
to unpack at startup. Keep the `.exe` together with the other files in that
folder (you can make a desktop shortcut to it).

### Option A — build it yourself on Windows
Double-click **`build.bat`** (or run it from a command prompt). It sets up a
virtual environment, installs everything, and produces:

```
dist\iPhoneMediaSync\iPhoneMediaSync.exe
```

### Option B — download a pre-built app from GitHub
Every push builds the app on a Windows runner.

- **Latest build:** repo **Actions → "Build Windows EXE"** → download the
  **`iPhoneMediaSync-windows`** artifact (a zip). Unzip it anywhere and run
  `iPhoneMediaSync.exe`.
- **Tagged releases:** pushing a version tag publishes the zip to the repo's
  **Releases** page with a permanent download link:

  ```bat
  git tag v1.0.0
  git push origin v1.0.0
  ```

> Windows SmartScreen may warn about an unsigned app — choose
> *More info → Run anyway*. To use a custom icon, drop an `assets\app.ico`
> file before building.

## Project layout

```
src/iphone_media_sync/
  device/    device detection + AFC media access (pymobiledevice3)
  core/      scanning, dedupe, backup, the backed-up index
  ui/        PySide6 windows, tabs, and the thumbnail grid
```

## Status

First cut. Built against `pymobiledevice3`'s AFC media interface. Real-device
testing happens on a Windows machine with an iPhone attached.
