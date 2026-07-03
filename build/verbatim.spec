# PyInstaller spec per Verbatim (Windows, onedir).
# Build:  pyinstaller build/verbatim.spec --noconfirm   (dalla cartella del progetto)
#
# Strategia: NON impacchettiamo i modelli (troppo grandi). Al primo avvio l'app li scarica
# una volta in %LOCALAPPDATA%\Verbatim\models e poi funziona offline (vedi app/setup.py).
# I pesi di silero-vad e resemblyzer sono dentro i pacchetti -> vanno raccolti come dati.

import os
import shutil
import importlib.metadata as _md
from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = os.path.dirname(os.path.abspath(SPECPATH))  # cartella del progetto (build/ -> ..)

# --- fix webrtcvad-wheels ---------------------------------------------------
# resemblyzer importa 'webrtcvad'; lo forniamo con 'webrtcvad-wheels'. Il hook PyInstaller
# fa copy_metadata('webrtcvad') che fallisce perché i metadata si chiamano 'webrtcvad-wheels'.
# Creiamo un alias dei metadata (idempotente) così il hook trova la distribuzione 'webrtcvad'.
try:
    _md.distribution("webrtcvad")
except _md.PackageNotFoundError:
    _src = _md.distribution("webrtcvad-wheels")._path
    _dst = os.path.join(os.path.dirname(_src), f"webrtcvad-{_md.version('webrtcvad-wheels')}.dist-info")
    if not os.path.exists(_dst):
        shutil.copytree(_src, _dst)

datas = [(os.path.join(ROOT, "app", "static"), "app/static")]
binaries = []
hiddenimports = [
    "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets", "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    "sklearn.utils._typedefs", "sklearn.neighbors._partition_nodes",
    # moduli dell'app (config è alla radice del progetto, fuori dal package)
    "config", "app.main", "app.setup", "app.export",
    "app.pipeline.transcribe", "app.pipeline.audio", "app.pipeline.vad",
    "app.pipeline.literal", "app.pipeline.readable", "app.pipeline.diarize",
    "webrtcvad",
]

# Raccogli interamente i pacchetti con dati/estensioni native non rilevati in automatico.
for pkg in ("transformers", "onnx_asr", "onnxruntime", "silero_vad", "resemblyzer",
            "librosa", "soundfile", "sklearn", "scipy", "torchaudio"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h

# torch è grande e ha hook propri: raccogliamo solo i dati necessari.
datas += collect_data_files("torch")

block_cipher = None

a = Analysis(
    [os.path.join(ROOT, "app", "launcher.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter.test", "matplotlib", "pytest"],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Verbatim",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # finestra senza console (windowed)
    icon=None,              # aggiungere build/verbatim.ico se disponibile
)
coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name="Verbatim",
)
