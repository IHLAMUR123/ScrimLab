@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo  ScrimLab - Windows kurulum
echo ============================================================
echo.

REM ---------- 1. Python bul ----------
set "PY_CMD="
py -3.12 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3.12"
if not defined PY_CMD py -3 -c "import sys" >nul 2>&1 && set "PY_CMD=py -3"
if not defined PY_CMD if exist "%LOCALAPPDATA%\Python\bin\python.exe" set "PY_CMD="%LOCALAPPDATA%\Python\bin\python.exe""
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe""
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_CMD="%LOCALAPPDATA%\Programs\Python\Python313\python.exe""
if not defined PY_CMD if exist "%ProgramFiles%\Python312\python.exe" set "PY_CMD="%ProgramFiles%\Python312\python.exe""
if not defined PY_CMD if exist "%ProgramFiles%\Python313\python.exe" set "PY_CMD="%ProgramFiles%\Python313\python.exe""
if not defined PY_CMD python -c "import sys" >nul 2>&1 && set "PY_CMD=python"

if not defined PY_CMD (
  echo [HATA] Python bulunamadi.
  echo.
  echo   https://www.python.org/downloads/ adresinden Python 3.12+ kurun.
  echo   Kurulum ekraninda "Add python.exe to PATH" secenegini isaretleyin.
  echo   Sonra bu dosyayi yeniden calistirin.
  echo.
  pause
  exit /b 1
)

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,12) else 1)" >nul 2>&1
if errorlevel 1 (
  echo [HATA] Python 3.12 veya uzeri gerekli. Bulunan surum:
  %PY_CMD% --version
  echo.
  pause
  exit /b 1
)
echo [1/7] Python hazir.

REM ---------- 2. Sanal ortam ----------
echo [2/7] Sanal ortam (.venv) hazirlaniyor...
if not exist ".venv\Scripts\python.exe" (
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo [HATA] Sanal ortam olusturulamadi.
    pause
    exit /b 1
  )
)
set "VENV_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo [HATA] .venv\Scripts\python.exe bulunamadi.
  pause
  exit /b 1
)

REM ---------- 3. Bagimliliklar ----------
echo [3/7] Bagimliliklar kuruluyor...
"%VENV_PY%" -m pip install --upgrade pip wheel --disable-pip-version-check -q
"%VENV_PY%" -m pip install -r requirements.txt --disable-pip-version-check -q
if errorlevel 1 (
  echo [HATA] requirements.txt kurulamadi.
  echo        Internet baglantinizi kontrol edin.
  pause
  exit /b 1
)

REM ---------- 4. Yapilandirma ----------
echo [4/7] Yapilandirma kontrol ediliyor...
if not exist ".env" (
  copy /y ".env.example" ".env" >nul
  echo     .env dosyasi .env.example'dan olusturuldu.
)

"%VENV_PY%" -c "import re,sys; t=open('.env',encoding='utf-8').read(); m=re.search(r'(?m)^TOKEN=(.*)$',t); raise SystemExit(0 if m and m.group(1).strip() else 1)"
if errorlevel 1 (
  echo.
  echo     TOKEN henuz girilmemis. .env dosyasi Notepad ile aciliyor.
  echo     TOKEN= satirina bot tokenini yazip kaydedin, sonra bu pencereye donun.
  start "" notepad ".env"
  pause
)
"%VENV_PY%" -c "import re,sys; t=open('.env',encoding='utf-8').read(); m=re.search(r'(?m)^TOKEN=(.*)$',t); raise SystemExit(0 if m and m.group(1).strip() else 1)"
if errorlevel 1 echo     [UYARI] TOKEN hala bos. Bot baslamaz; .env dosyasini duzenleyin.

REM ---------- 5. Veritabani ----------
echo [5/7] Veritabani klasoru...
if not exist "db" mkdir "db"

REM ---------- 6. Sozdizimi ----------
echo [6/7] Sozdizimi kontrolu...
"%VENV_PY%" -m compileall -q main.py core cogs tests
if errorlevel 1 echo     [UYARI] Bazi dosyalar derlenemedi.

REM ---------- 7. Testler ----------
echo [7/7] Testler...
"%VENV_PY%" -m pip install -r requirements-dev.txt --disable-pip-version-check -q
"%VENV_PY%" -m pytest -q
if errorlevel 1 echo     [UYARI] Testler basarisiz oldu.

echo.
echo ============================================================
echo  Kurulum tamam.
echo.
echo  Baslatmak icin : start.bat
echo  Elle           : .venv\Scripts\python.exe main.py
echo ============================================================
echo.

if /i "%~1"=="/run" (
  echo Bot baslatiliyor...
  "%VENV_PY%" main.py
)

pause
endlocal
