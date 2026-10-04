@echo off
chcp 65001 >nul
echo === Installazione di JARVIS ===
python -m venv .venv || (echo Python non trovato: installalo da https://www.python.org/ && pause && exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Installazione completata. Apri il file .env e inserisci la tua ANTHROPIC_API_KEY.
echo Poi avvia JARVIS con avvia_jarvis.bat
pause
