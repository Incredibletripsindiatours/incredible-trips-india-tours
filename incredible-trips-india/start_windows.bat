@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -m venv .venv
  if errorlevel 1 (echo Python 3.10+ is required.& pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (echo Could not install dependencies.& pause & exit /b 1)
if not exist "data\site.db" (
  echo Database will be created automatically.
)
echo.
echo If this is your first run, press Ctrl+C and run: .venv\Scripts\python.exe create_admin.py
 echo Open http://127.0.0.1:8000 in your browser.
".venv\Scripts\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
