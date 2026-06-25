# iPhone Media Sync v1.5.0

A batch of workflow/usability features (all local, no paid services), plus the
build fix that the empty v1.4.0/failed v1.4.1 needed.

## New in 1.5.0
- **Video poster frames** — videos now show a real thumbnail (extracted with a
  bundled ffmpeg) instead of a placeholder. Cheap: the clip is already
  downloaded for hashing; cached after the first scan; skips very large clips.
- **Filename normalization on backup** — optional: rename copies to their
  capture date (`YYYYMMDD_HHMMSS`). Toggle in Settings.
- **Open backup folder / Open log folder / View last manifest** — under a new
  **Tools** menu.
- **Sort controls** — sort any grid by newest/oldest, largest/smallest, or
  name (in the filter bar).
- **Range/multi-select + invert** — ctrl/shift-click to highlight a range, then
  "Check selected"; plus an "Invert" button.
- **Date-range filter** — show only items before/after a date (great for
  archiving old media).

## Carried over (first working build of these)
- Full-size preview (double-click a thumbnail), quarantine browser/restore,
  offline OCR text detection in Probably Delete, and the Overview dashboard
  (these shipped in the code for 1.4.0 but that release built empty due to a
  packaging bug, now fixed).

## Build fix
- The Tesseract bundling appended `Tree` 3-tuples to PyInstaller's `datas`
  (which expects 2-tuples), crashing packaging. Moved to `a.datas` after
  Analysis; `collect_all` calls are now fault-tolerant; the build step fails
  loudly instead of publishing an empty release.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.5.0.exe`
- **Portable:** `iPhoneMediaSync-windows.zip`

On first connection, unlock the iPhone and tap "Trust This Computer."
