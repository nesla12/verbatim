# Verbatim — build della cartella PORTABLE (Python integrato + dipendenze).
# Produce  build\portable\Verbatim\  pronta per Inno Setup (installer\verbatim.iss).
#
# Strategia affidabile per app torch/ML: NIENTE PyInstaller. Usiamo il Python "embeddable"
# ufficiale, ci installiamo dentro le dipendenze (dalla cache pip, niente ri-download di torch),
# copiamo il codice e un avvio .bat. I modelli si scaricano al primo avvio (schermata in app).
#
# Uso:  powershell -ExecutionPolicy Bypass -File build\build_portable.ps1

$ErrorActionPreference = "Stop"

# ISOLAMENTO (critico): senza questo, il Python embeddable vede i pacchetti globali in
# %APPDATA%\Python e pip li considera "gia' soddisfatti", lasciando la cartella portable VUOTA
# (funzionerebbe solo su questa macchina). Forziamo l'isolamento totale.
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONPATH = ""

$PyVer   = "3.12.6"
$Root    = Split-Path -Parent $PSScriptRoot           # cartella del progetto
$Out     = Join-Path $Root "build\portable\Verbatim"
$PyDir   = Join-Path $Out "python"
$Cache   = Join-Path $Root "build\_dl"

function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }

# 0) pulizia + cartelle
if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Force -Path $PyDir, $Cache | Out-Null

# 1) Python embeddable
Step "Scarico Python $PyVer embeddable"
$embZip = Join-Path $Cache "python-embed.zip"
if (-not (Test-Path $embZip)) {
  Invoke-WebRequest "https://www.python.org/ftp/python/$PyVer/python-$PyVer-embed-amd64.zip" -OutFile $embZip
}
Expand-Archive $embZip -DestinationPath $PyDir -Force

# 2) abilita 'import site' (per trovare i pacchetti pip) e i percorsi dell'app
Step "Configuro il Python integrato"
$pth = Get-ChildItem $PyDir -Filter "python3*._pth" | Select-Object -First 1
(Get-Content $pth.FullName) -replace '#\s*import site', 'import site' | Set-Content $pth.FullName
Add-Content $pth.FullName "`r`n.."   # aggiunge la cartella dell'app (un livello sopra python\)

# 3) pip dentro l'embeddable
Step "Installo pip"
$getpip = Join-Path $Cache "get-pip.py"
if (-not (Test-Path $getpip)) { Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip }
& "$PyDir\python.exe" $getpip --no-warn-script-location
if ($LASTEXITCODE -ne 0) { throw "get-pip fallito" }

# 4) dipendenze (dalla cache pip: niente ri-download di torch)
Step "Installo le dipendenze (puo' richiedere qualche minuto)"
& "$PyDir\python.exe" -m pip install --no-warn-script-location -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install requirements fallito" }
& "$PyDir\python.exe" -m pip install --no-warn-script-location resemblyzer --no-deps
if ($LASTEXITCODE -ne 0) { throw "pip install resemblyzer fallito" }

# 5) copia del codice dell'app
Step "Copio il codice dell'app"
Copy-Item (Join-Path $Root "app")       (Join-Path $Out "app") -Recurse -Force
Copy-Item (Join-Path $Root "config.py") $Out -Force
Copy-Item (Join-Path $Root "setup_models.py") $Out -Force
Copy-Item (Join-Path $Root "README.md") $Out -Force
# niente cartelle di sviluppo (projects/, tests/, build/) nel pacchetto

# 5b) ffmpeg (se presente in build\_dl\ffmpeg.exe): l'app lo trova accanto a se stessa
$ff = Join-Path $Cache "ffmpeg.exe"
if (Test-Path $ff) { Step "Includo ffmpeg"; Copy-Item $ff $Out -Force }
else { Write-Host "NB: ffmpeg.exe non trovato in build\_dl -> l'insegnante dovra' avere ffmpeg nel PATH" -ForegroundColor Yellow }

# 6) avvio
Step "Creo l'avvio Verbatim.bat"
@'
@echo off
title Verbatim - non chiudere questa finestra mentre lavori
cd /d "%~dp0"
REM isolamento: usa SOLO i pacchetti dentro questa cartella, mai quelli globali
set PYTHONNOUSERSITE=1
set PYTHONPATH=
echo Avvio di Verbatim in corso... il browser si aprira' tra pochi secondi.
echo Per uscire, chiudi questa finestra.
python\python.exe -m app.launcher
'@ | Set-Content -Encoding ascii (Join-Path $Out "Verbatim.bat")

Step "FATTO. Cartella portable: $Out"
Write-Host "Provala con:  `"$Out\Verbatim.bat`"" -ForegroundColor Green
