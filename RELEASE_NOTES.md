# iPhone Media Sync v1.3.0

## New in 1.3.0 — "Probably Delete" tab
- A new tab that surfaces **likely-ephemeral images** — message/text
  screenshots, memes, and images saved from the web or chats — that are usually
  used in the moment and not worth long-term storage.
- Candidates are scored from fast on-device signals (screenshot detection,
  missing camera EXIF, flat/low-color graphics, and high white area typical of
  text/messages), listed checked-by-default, each with the reason it was
  flagged.
- A **sensitivity** slider lets you widen or narrow what gets flagged.
- Deletion uses the same safety net as everywhere else: confirmation, optional
  quarantine-first, and (by default) only items already backed up. Nothing is
  ever deleted automatically.

## Recent history
- **1.2.4** — installer bootstraps Apple Mobile Device Support.
- **1.2.3** — bundle `pywin32`; **1.2.2** — pin `pymobiledevice3<8` (async fix);
  **1.2.1** — Diagnostics + log file.
- **1.2.0** — Windows installer, quarantine-on-delete, CI.
- **1.1.0** — Live Photos, EXIF dates, filters, best-of-burst, dry-run,
  resume/retry, scan cache, cleanup candidates, manifest, storage readouts,
  folder template, update checker, light theme.

## Download
- **Installer (recommended):** `iPhoneMediaSync-Setup-1.3.0.exe`
- **Portable:** `iPhoneMediaSync-windows.zip`

On first connection, unlock the iPhone and tap "Trust This Computer."
