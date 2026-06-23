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

if exist "dist\iPhoneMediaSync\iPhoneMediaSync.exe" (
    echo.
    echo ============================================================
    echo  Build complete:  dist\iPhoneMediaSync\iPhoneMediaSync.exe
    echo  Open the dist\iPhoneMediaSync folder and double-click
    echo  iPhoneMediaSync.exe to launch the app. Keep the .exe with
    echo  the other files in that folder.
    echo ============================================================
) else (
    echo.
    echo Build did not produce the executable -- see errors above.
    exit /b 1
)

endlocal
