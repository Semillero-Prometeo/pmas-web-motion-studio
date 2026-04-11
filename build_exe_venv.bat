@echo off
echo ========================================
echo  R-ONE Motion Studio - Build con venv
echo ========================================

python -m venv venv_build
call venv_build\Scripts\activate.bat

pip install --upgrade pip --quiet
pip install pyinstaller==6.11.1 --quiet
pip install PyQt5==5.15.11 --quiet
pip install pyserial==3.5 --quiet
pip install openai --quiet

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

pyinstaller ^
  --name "R-ONE_Motion_Studio" ^
  --noconfirm ^
  --windowed ^
  --optimize 2 ^
  --exclude-module matplotlib ^
  --exclude-module numpy ^
  --exclude-module pandas ^
  --exclude-module scipy ^
  --exclude-module PIL ^
  --exclude-module tkinter ^
  --exclude-module unittest ^
  --exclude-module turtle ^
  --exclude-module curses ^
  --exclude-module pygments ^
  --exclude-module IPython ^
  --exclude-module jedi ^
  --exclude-module parso ^
  --exclude-module test ^
  --collect-submodules serial ^
  --collect-submodules openai ^
  interfaz_record9_5_1.py

call venv_build\Scripts\deactivate.bat

echo.
echo ========================================
if exist "dist\R-ONE_Motion_Studio\R-ONE_Motion_Studio.exe" (
    echo  BUILD EXITOSO
    echo  Carpeta: dist\R-ONE_Motion_Studio\
) else (
    echo  ERROR en el build
)
echo ========================================
pause
