@echo off
chcp 65001 >nul
set "SCRIPT_DIR=%~dp0"
set "PYTHON_PATH=M:\venv_webscraper\Scripts\python.exe"
set "SCRIPT_NAME=webscraper_NEW.py"
set "OUTPUT_DIR=%SCRIPT_DIR%binari"
set "ICON_NAME=webscraper_icon.ico"

cd /d "%SCRIPT_DIR%"

if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo ============================================
echo === BUILDING EXECUTABLE FROM: %SCRIPT_NAME%
echo === OUTPUT DIRECTORY: %OUTPUT_DIR%
echo ============================================

%PYTHON_PATH% -m PyInstaller ^
  --onefile ^
  --noconfirm ^
  --clean ^
  --name webscraper ^
  --icon=%ICON_NAME% ^
  --hidden-import=selenium ^
  --hidden-import=tkinter ^
  --hidden-import=dateutil.parser ^
  --hidden-import=webdriver_manager ^
  --hidden-import=psutil ^
  --hidden-import=PIL.Image ^
  --hidden-import=PIL.ImageTk ^
  --hidden-import=imageio ^
  --hidden-import=imageio.plugins.ffmpeg ^
  --hidden-import=bs4 ^
  --hidden-import=numpy.core._methods ^
  --hidden-import=numpy.lib.format ^
  --hidden-import=sklearn ^
  --hidden-import=sklearn.feature_extraction ^
  --hidden-import=sklearn.feature_extraction.text ^
  --hidden-import=sklearn.metrics ^
  --hidden-import=sklearn.metrics.pairwise ^
  --exclude-module=PyQt5 ^
  --distpath "%OUTPUT_DIR%" ^
  "%SCRIPT_NAME%"

if exist "config.json" (
    echo Copia config.json nella cartella di output...
    copy /Y "config.json" "%OUTPUT_DIR%\config.json" >nul
) else (
    echo Nessun config.json trovato. Salto la copia.
)

for %%F in ("%OUTPUT_DIR%\webscraper.exe") do set SIZE=%%~zF
set /a SIZE_MB=%SIZE%/1024/1024
echo === Dimensione finale dell'eseguibile: %SIZE_MB% MB

echo ============================================
echo === DONE. Executable created in: %OUTPUT_DIR%
echo ============================================
pause