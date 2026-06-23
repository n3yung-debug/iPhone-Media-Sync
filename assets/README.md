# App assets

## Application icon

Put your icon here, named either:

```
assets/app.ico        (preferred)
assets/favicon.ico    (also accepted)
```

- It must be a Windows `.ico` file (not `.png`/`.jpg`). If you have a PNG,
  convert it to `.ico` first (any online converter or an image editor works;
  256×256 is a good size).
- When present, it is used automatically as:
  - the executable's icon (baked in by the PyInstaller build), and
  - the window / taskbar icon at runtime.
- No code changes are needed — the build and the app both look for this exact
  path. If the file is missing, the app falls back to the default icon.
