# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build a single-file Windows .exe.

Build with:  pyinstaller iphone-media-sync.spec
Output:      dist/iPhoneMediaSync.exe
"""

from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

# These packages load submodules / data files dynamically, so collect them
# fully rather than relying on static import analysis. (PySide6 is handled by
# PyInstaller's own bundled hook, so we deliberately don't collect it here —
# that would pull in every Qt module and bloat the build.)
for pkg in ("pymobiledevice3", "pillow_heif", "imagehash"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="iPhoneMediaSync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,            # windowed app, no console window
    disable_windowed_traceback=False,
    icon="assets/app.ico" if __import__("os").path.exists("assets/app.ico") else None,
)
