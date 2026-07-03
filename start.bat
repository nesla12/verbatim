@echo off
REM Verbatim - avvio del programma. Apre il browser su http://127.0.0.1:8000
cd /d "%~dp0"
echo Avvio di Verbatim... la finestra del browser si aprira' tra pochi secondi.
start "" http://127.0.0.1:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
