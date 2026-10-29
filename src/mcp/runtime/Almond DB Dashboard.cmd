@echo off
setlocal
if exist "%~dp0..\..\engine\.venv\Scripts\python.exe" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0dashboard.ps1" -PickFile
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0dashboard.ps1" -PickFile -Development
)
if errorlevel 1 pause
