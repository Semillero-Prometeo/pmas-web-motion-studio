@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo  R-ONE Motion Studio (suelto / Windows)
echo ========================================

set "PY=python"
where py >nul 2>&1 && set "PY=py -3"

if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual .venv ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo No se encontro Python. Instala Python 3.11 o superior y marca "Add python.exe to PATH".
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip --quiet
python -m pip install -e ".[dev]"
if errorlevel 1 (
  echo Fallo la instalacion de dependencias.
  pause
  exit /b 1
)

if not exist "data\sequences" mkdir "data\sequences"

set "MOTION_STUDIO_PORT=4210"
set "MOTION_STUDIO_DATA_DIR=%CD%\data\sequences"

echo.
echo  Editor:  http://127.0.0.1:4210
echo  JSON:    %MOTION_STUDIO_DATA_DIR%
echo  Ctrl+C para detener.
echo ========================================
echo.

python -m uvicorn src.app:app --host 127.0.0.1 --port 4210 --reload --reload-dir src
pause
