@echo off
setlocal

where powershell.exe >nul 2>nul
if errorlevel 1 (
    echo PowerShell was not found. This installer requires Windows PowerShell 5.1 or newer.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-OrvilleFreeCAD.ps1" %*
set EXITCODE=%ERRORLEVEL%

echo.
if not "%EXITCODE%"=="0" (
    echo Orville installer failed with exit code %EXITCODE%.
) else (
    echo Orville installer finished.
)
pause
exit /b %EXITCODE%
