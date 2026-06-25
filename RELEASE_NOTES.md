# iPhone Media Sync v1.5.1

## Fix in 1.5.1 — no more console flashes
- Stopped a **CMD/console window from flashing** during analysis. The video
  poster-frame feature (added in 1.5.0) launches a bundled `ffmpeg` per video,
  and on Windows a console program briefly pops a window. It now runs with
  `CREATE_NO_WINDOW`, so it's fully silent/background.
- Applied the same no-window fix to the OCR engine (Tesseract) used by the
  "Refine with text detection" button.

## From 1.5.0
- Video poster frames, filename normalization on backup, Tools menu
  (open backup folder / log / last manifest), grid sort, range/shift
  multi-select + invert, and a date-range filter — plus the first working
  build of preview, quarantine browser, OCR, and the Overview dashboard.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.5.1.exe`
- **Portable:** `iPhoneMediaSync-windows.zip`

On first connection, unlock the iPhone and tap "Trust This Computer."
