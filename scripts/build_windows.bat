@echo off
REM Сборка одиночного .exe для Windows (запускать на ПК с Windows).
REM Требуется: Python 3.10+ с pip. Результат: dist\OttomanCampaign\OttomanCampaign.exe
cd /d "%~dp0.."
python -m pip install --upgrade pip pygame pyinstaller
pyinstaller --noconfirm --clean --windowed --name OttomanCampaign ^
  --collect-all pygame ^
  --add-data "assets;assets" ^
  main.py
echo.
echo Готово. Исполняемый файл в папке dist\OttomanCampaign\
pause
