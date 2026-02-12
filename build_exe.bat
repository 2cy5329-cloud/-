@echo off
setlocal

REM Usage:
REM   1) py -m pip install pyinstaller
REM   2) build_exe.bat

py -m PyInstaller --noconsole --onefile --name PrintSpooler_Service PrintSpooler_Service.pyw

echo.
echo Build complete. Check dist\PrintSpooler_Service.exe
endlocal
