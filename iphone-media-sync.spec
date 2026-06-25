# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build a folder (one-dir) Windows app.

A folder build launches fast because nothing has to unpack at startup.

Build with:  pyinstaller iphone-media-sync.spec
Output:      dist/iPhoneMediaSync/iPhoneMediaSync.exe   (run this)
"""

import os

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# Bundle the app icon (if present) so it can also be shown at runtime as the
# window / taskbar icon, not just baked into the .exe. Accept either name.
icon_candidates = ["assets/app.ico", "assets/favicon.ico"]
icon_file = next((p for p in icon_candidates if os.path.exists(p)), None)
if icon_file:
    datas.append((icon_file, "assets"))

# These packages load submodules / data files dynamically, so collect them
# fully rather than relying on static import analysis. (PySide6 is handled by
# PyInstaller's own bundled hook, so we deliberately don't collect it here —
# that would pull in every Qt module and bloat the build.)
for pkg in ("pymobiledevice3", "pillow_heif", "imagehash"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# pymobiledevice3 imports win32security lazily on Windows (via pywin32) but
# doesn't declare it, so PyInstaller's analysis misses it. Force-bundle the
# pywin32 modules it needs.
hiddenimports += [
    "win32security",
    "win32api",
    "win32file",
    "win32con",
    "pywintypes",
    "pythoncom",
]

# Bundle the Tesseract OCR engine if the build placed it under vendor/tesseract
# (see the release/build workflows). Lets offline text detection work without a
# separate install. Wrapped defensively so a bundling hiccup can never break
# the whole build — worst case OCR just reports "unavailable".
try:
    from PyInstaller.building.datastruct import Tree

    if os.path.isdir("vendor/tesseract"):
        datas += Tree("vendor/tesseract", prefix="tesseract")
except Exception as _ocr_exc:  # noqa: BLE001
    print(f"NOTE: skipping Tesseract bundle: {_ocr_exc}")

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtQuick", "PySide6.Qt3DCore"],
    noarchive=False,
)

pyz = PYZ(a.pure)

# Folder build: EXE holds only the bootloader/scripts; binaries and data are
# placed alongside it by COLLECT, so launching doesn't unpack anything.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="iPhoneMediaSync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # windowed app, no console window
    disable_windowed_traceback=False,
    icon=icon_file,           # detected above (app.ico / favicon.ico), or None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="iPhoneMediaSync",
)
