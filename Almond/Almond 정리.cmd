@echo off
chcp 65001 >nul
title Almond 정리
"%~dp0_engine\.venv\Scripts\python.exe" -B -X utf8 "%~dp0_engine\purge.py"
pause
