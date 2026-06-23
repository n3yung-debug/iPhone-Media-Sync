@echo off
REM Build iPhoneMediaSync.exe on Windows.
REM Usage: double-click this file, or run "build.bat" in a command prompt.

setlocal

echo === Creating / using virtual environment ===
if not exist ".venv\" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo === Installing dependencies ===
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo === Building executable ===
pyinstaller --noconfirm --clean iphone-media-sync.spec

if not exist "dist\iPhoneMediaSync\iPhoneMediaSync.exe" (
    echo.
    echo Build did not produce the executable -- see errors above.
    exit /b 1
)

echo === Building installer (optional) ===
REM If Inno Setup's compiler (iscc) is on PATH, also produce a Setup .exe.
where iscc >nul 2>nul
if %errorlevel%==0 (
    iscc installer\iphone-media-sync.iss
    echo  Installer written to installer\output\
) else (
    echo  Inno Setup ^(iscc^) not found on PATH; skipping installer.
    echo  Install it from https://jrsoftware.org/isdl.php to build a Setup.exe.
)

echo.
echo ============================================================
echo  Build complete:  dist\iPhoneMediaSync\iPhoneMediaSync.exe
echo  Open the dist\iPhoneMediaSync folder and double-click
echo  iPhoneMediaSync.exe to launch the app. Keep the .exe with
echo  the other files in that folder.
echo ============================================================

endlocal
