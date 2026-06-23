# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: build a folder (one-dir) Windows app.

A folder build launches fast because nothing has to unpack at startup.

Build with:  pyinstaller iphone-media-sync.spec
Output:      dist/iPhoneMediaSync/iPhoneMediaSync.exe   (run this)
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
    icon="assets/app.ico" if __import__("os").path.exists("assets/app.ico") else None,
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
