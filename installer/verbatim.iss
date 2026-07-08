; Inno Setup — installer di Verbatim per gli insegnanti.
; Compilare con Inno Setup Compiler DOPO la build portable:
;   powershell -ExecutionPolicy Bypass -File build\build_portable.ps1
; Impacchetta build\portable\Verbatim\ (Python integrato + dipendenze) e crea i collegamenti.
; Per l'insegnante: doppio clic sull'installer, poi icona "Verbatim" sul desktop.
;
; ffmpeg: se in build\portable\Verbatim\ è presente ffmpeg.exe, viene installato con l'app
; e trovato automaticamente (vedi audio.py). Altrimenti l'insegnante deve avere ffmpeg.

#define MyAppName "Verbatim"
#define MyAppVersion "1.0"
#define MyAppLauncher "Verbatim.bat"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Lorenzo Nesler - aiautomationcoach.com
AppPublisherURL=https://aiautomationcoach.com
; INSTALLAZIONE PER-UTENTE (niente amministratore, niente UAC): affidabile e senza attriti.
; L'installazione in Program Files richiedeva l'elevazione e su alcune macchine causava
; un errore all'avvio automatico ("CallSpawnServer") e copie incomplete dei file. Con
; PrivilegesRequired=lowest il programma si installa in %LocalAppData%\Programs\Verbatim,
; cartella scrivibile dall'utente: nessuna elevazione, avvio affidabile.
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.\output
OutputBaseFilename=Verbatim-Setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; L'eseguibile non è firmato: Windows mostrerà "Editore sconosciuto" (vedi BUILD.md R2).

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[Files]
; tutta la cartella portable (Python integrato + dipendenze + app)
Source: "..\build\portable\Verbatim\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
; collegamenti che avviano il .bat (apre il browser sull'app)
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppLauncher}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppLauncher}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crea un collegamento sul Desktop"; GroupDescription: "Collegamenti:"

[Run]
Filename: "{app}\{#MyAppLauncher}"; Description: "Avvia Verbatim ora"; Flags: nowait postinstall skipifsilent shellexec
