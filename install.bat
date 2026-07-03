@echo off
REM Verbatim - installazione delle dipendenze (una sola volta).
cd /d "%~dp0"
echo Installazione dipendenze principali...
python -m pip install -r requirements.txt
if errorlevel 1 goto :err
echo Installazione modulo interlocutori (resemblyzer, senza dipendenze)...
python -m pip install resemblyzer --no-deps
if errorlevel 1 goto :err
echo Scaricamento modelli (una tantum, serve connessione)...
python setup_models.py
if errorlevel 1 goto :err
echo.
echo Fatto. Avvia il programma con start.bat
pause
exit /b 0
:err
echo.
echo Si e' verificato un errore durante l'installazione.
pause
exit /b 1
