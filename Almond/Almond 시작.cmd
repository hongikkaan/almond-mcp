@echo off
chcp 65001 >nul
title Almond 시작
powershell.exe -NoLogo -NoProfile -STA -File "%~dp0_engine\launch.ps1" -ModelPath "%~1"
if errorlevel 1 pause
