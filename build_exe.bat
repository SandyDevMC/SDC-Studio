@echo off
setlocal
cd /d "%~dp0"

echo [SDC-Studio] Installing build dependencies...
py -3 -m pip install -r requirements.txt
if errorlevel 1 goto :error
py -3 -m pip install pyinstaller>=6.0
if errorlevel 1 goto :error

echo [SDC-Studio] Building windowed executable...
py -3 -m PyInstaller --noconfirm --clean SDC-Studio.spec
if errorlevel 1 goto :error

echo.
echo Done: dist\SDC-Studio.exe
pause
exit /b 0

:error
echo.
echo Build failed. Check the messages above.
pause
exit /b 1
