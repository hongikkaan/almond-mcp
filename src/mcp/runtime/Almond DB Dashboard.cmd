@echo off
setlocal
set "dashboardPowerShell="
if exist "%ProgramFiles%\PowerShell\7\pwsh.exe" set "dashboardPowerShell=%ProgramFiles%\PowerShell\7\pwsh.exe"
if not defined dashboardPowerShell if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe" set "dashboardPowerShell=%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe"
if not defined dashboardPowerShell set "dashboardPowerShell=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "PATH=%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%"
if not exist "%dashboardPowerShell%" (
  echo PowerShell was not found at "%dashboardPowerShell%".
  pause
  exit /b 1
)
"%dashboardPowerShell%" -NoProfile -ExecutionPolicy Bypass -STA -File "%~dp0dashboard.ps1" -PickFile
if errorlevel 1 (
  pause
  exit /b 1
)
