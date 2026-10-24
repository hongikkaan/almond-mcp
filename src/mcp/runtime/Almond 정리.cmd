@echo off
chcp 65001 >nul
title Almond 정리
"%~dp0..\..\engine\.venv\Scripts\python.exe" -B -X utf8 "%~dp0purge.py"
pause
