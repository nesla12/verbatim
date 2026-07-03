# BUILD — creare l'installer di Verbatim per gli insegnanti (Windows)

Per sviluppatori. Produce un installer (`Verbatim-Setup.exe`) che gli insegnanti avviano con
un doppio clic: installa l'app con un **Python integrato** e tutte le dipendenze, e crea
un'icona sul desktop. Nessun Python da installare a mano, nessun terminale.

> **Perché non PyInstaller?** Impacchettare torch + transformers in un singolo `.exe` con
> PyInstaller è risultato fragile e lentissimo (analisi di ore, artefatto da 3-5 GB, falsi
> positivi antivirus). La via affidabile per un'app ML in Python è distribuire un **Python
> embeddable** con le dipendenze pre-installate. È quello che fa lo script qui sotto.

I modelli NON sono inclusi nell'installer: al primo avvio l'app mostra una schermata e li
scarica una volta in `%LOCALAPPDATA%\Verbatim\models`, poi funziona offline.

## Prerequisiti (macchina di build)
- Windows 10/11 a 64 bit con Python 3.12 e le dipendenze già installate (`install.bat`).
- Connessione a Internet (lo script scarica il Python embeddable e, se non in cache, i wheel).
- [Inno Setup](https://jrsoftware.org/isdl.php) per creare l'installer (passo 2).

## 1. Cartella portable (Python integrato + dipendenze)
Dalla cartella del progetto:

```
powershell -ExecutionPolicy Bypass -File build\build_portable.ps1
```

Cosa fa lo script (`build/build_portable.ps1`):
1. scarica il **Python 3.12.6 embeddable** ufficiale in `build\portable\Verbatim\python\`;
2. abilita `import site` e i percorsi dell'app nel file `._pth`;
3. installa `pip` e tutte le dipendenze (`requirements.txt` + `resemblyzer --no-deps`);
4. copia il codice dell'app e crea `Verbatim.bat` (avvio + apertura browser).

Risultato: `build\portable\Verbatim\` (~2-3 GB per via di torch). Testala con:

```
build\portable\Verbatim\Verbatim.bat
```

Deve aprirsi il browser sull'app. Alla prima esecuzione compare la schermata di download modelli.

### Includere ffmpeg (consigliato)
Gli insegnanti potrebbero non avere ffmpeg. Copia un `ffmpeg.exe` dentro
`build\portable\Verbatim\` prima del passo 2: l'app lo trova in automatico (vedi `audio.py`).

## 2. Installer (Inno Setup)
Apri `installer\verbatim.iss` con Inno Setup Compiler e premi **Compile** (oppure
`iscc installer\verbatim.iss`). Produce `installer\output\Verbatim-Setup.exe` con collegamenti
su Desktop e menu Start.

## 3. Firma del codice (opzionale)
L'app non è firmata: al primo avvio Windows SmartScreen mostra "Editore sconosciuto".
L'insegnante clicca **"Ulteriori informazioni" → "Esegui comunque"**. Per togliere l'avviso
serve un certificato di code-signing (a pagamento) da applicare con `signtool` all'installer.

## 4. Verifica su PC pulito
1. Avvia `Verbatim-Setup.exe`, completa l'installazione, apri l'icona sul desktop.
2. Compare "Preparazione iniziale" → "Scarica i modelli" (serve Internet una volta).
3. Trascina un file audio: verifica trascrizione, interlocutori, export .docx.
4. Riavvia SENZA Internet: la trascrizione deve continuare a funzionare (offline).

---
*I file PyInstaller (`build/verbatim.spec`, `app/launcher.py`) restano nel repo: `launcher.py`
è usato anche dalla versione portable per avviare il server e aprire il browser.*
