@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HATA] Kurulum bulunamadi. Once build.bat dosyasini calistirin.
  pause
  exit /b 1
)
if not exist ".env" (
  echo [HATA] .env bulunamadi. Once build.bat dosyasini calistirin.
  pause
  exit /b 1
)

echo ScrimLab baslatiliyor... (durdurmak icin Ctrl+C)
echo.
".venv\Scripts\python.exe" main.py

echo.
echo Bot kapandi.
pause
endlocal
