# Project guidance for Claude

## Versioning
- Single source of truth for the version is `__version__` in
  `src/iphone_media_sync/__init__.py`; keep `version` in `pyproject.toml` in
  sync with it.
- The version is surfaced in the app UI (window title and toolbar). When
  bumping the version, that display updates automatically.

## Application icon
- The app icon lives at `assets/app.ico` (preferred) or `assets/favicon.ico`
  (also accepted). It must be a Windows `.ico` file.
- It's used both as the `.exe` icon (baked in by the PyInstaller build) and as
  the window/taskbar icon at runtime. No code changes needed when replacing it.

## "Push a release"
When asked to "push a release", do it end to end (don't hand over manual
commands). The Claude Code remote sandbox's git proxy blocks pushing tag refs
(HTTP 403; only the working branch is pushable), so use GitHub Actions, which
runs with the repo token and can create tags/releases:

1. Bump the version in the single source of truth (see above); commit and push
   to the working branch.
2. Ensure `main` has all the code (create it from the working branch via the
   GitHub API if missing). Releases target `main`.
3. Ensure `RELEASE_NOTES.md` and the dispatchable
   `.github/workflows/release.yml` exist on the default branch. The workflow
   has `permissions: contents: write`, builds the Windows app, and publishes
   the release via `softprops/action-gh-release@v2` (`tag_name: vX.Y.Z`,
   `target_commitish: main`, `body_path: RELEASE_NOTES.md`, attaching the build
   zip). The build step is `continue-on-error` so the release still publishes
   if packaging has trouble.
4. Dispatch the workflow with the version input, poll until it completes, then
   confirm with the release URL.
5. Merge the working branch into `main` so `main` and the Releases page always
   reflect the latest version. The sandbox can't push to `main` directly, so do
   it via the GitHub API (`create_pull_request` base `main` + head working
   branch, then `merge_pull_request`). This is part of "push a release".

## Build / packaging
- `build.bat` builds a folder app locally: `dist/iPhoneMediaSync/iPhoneMediaSync.exe`.
- `.github/workflows/build-windows.yml` builds on every push (artifact) and on
  `v*` tags (release).
- Tests are Qt-free and run with `PYTHONPATH=src python -m pytest tests/`.
