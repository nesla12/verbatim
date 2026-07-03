"""Verbatim — configurazione centrale.

Tutti i percorsi e gli ID dei modelli vivono qui. Nessuna chiamata di rete a runtime:
i modelli vengono scaricati una sola volta durante il setup e poi usati offline.
"""
import os
import sys
from pathlib import Path

# Su Windows senza "Modalita' sviluppatore" la cache HuggingFace non puo' creare symlink:
# silenziamo l'avviso (il download avviene comunque, in modalita' copia).
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# --- identità applicazione ---
APP_VERSION = "1.0"
APP_AUTHOR = "Lorenzo Nesler"
APP_SITE = "https://aiautomationcoach.com"
APP_REPO = "https://github.com/nesla12/verbatim"

# --- percorsi ---
BASE_DIR = Path(__file__).resolve().parent
FROZEN = getattr(sys, "frozen", False)  # True quando impacchettato con PyInstaller


def _writable(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        t = p / ".write_test"
        t.write_text("x", encoding="utf-8")
        t.unlink()
        return True
    except Exception:
        return False


# Dati (progetti, audio, modelli) in una cartella utente SCRIVIBILE quando l'app è installata
# in una posizione di sola lettura (es. Program Files, dove un utente standard non può scrivere)
# o è congelata. In sviluppo, BASE_DIR è scrivibile e i dati restano accanto al codice.
if FROZEN or not _writable(BASE_DIR):
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Verbatim"
    os.environ.setdefault("HF_HOME", str(DATA_DIR / "models"))  # cache modelli scrivibile
else:
    DATA_DIR = BASE_DIR

PROJECTS_DIR = DATA_DIR / "projects"          # un file JSON per audio
UPLOADS_DIR = PROJECTS_DIR / "_audio"         # WAV 16 kHz mono normalizzati
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# marcatore locale: l'utente ha letto e accettato il disclaimer legale (una tantum).
LEGAL_ACCEPTED_FILE = DATA_DIR / ".accepted"

# --- formati di ingresso accettati (validazione lato client + info UI) ---
AUDIO_EXTS = ["wav", "mp3", "m4a", "aac", "ogg", "oga", "opus", "flac", "wma"]
VIDEO_EXTS = ["mp4", "mov", "mkv", "avi", "webm", "m4v"]
MAX_RECOMMENDED_MINUTES = 60   # durata massima consigliata per singolo file

# --- modelli ---
# LITERAL: vincolo NON negoziabile (vedi DECISIONS.md D2). CTC greedy puro, MAI LM.
LITERAL_MODEL_ID = "jonatasgrosman/wav2vec2-large-xlsr-53-italian"

# READABLE: livello di riferimento secondario (vedi DECISIONS.md D1).
# Backend selezionabile con un solo switch: "onnx" (default) oppure "faster-whisper".
READABLE_BACKEND = "onnx"
READABLE_ONNX_MODEL = "nemo-parakeet-tdt-0.6b-v3"   # onnx-asr model id
READABLE_WHISPER_MODEL = "large-v3"                 # usato solo se backend = faster-whisper

# --- audio / segmentazione ---
TARGET_SR = 16000            # wav2vec2 e parakeet vogliono 16 kHz mono
VAD_MIN_SILENCE_MS = 300     # silenzio minimo per separare due utterance
VAD_MIN_SPEECH_MS = 200      # scarta micro-segmenti
VAD_MAX_SEGMENT_S = 25.0     # tetto duro: parakeet v3 lavora bene < ~30 s

# wav2vec2: il feature extractor riduce di 320 campioni/frame a 16 kHz => 20 ms/frame.
# Il timestamp esatto viene comunque ricalcolato per-segmento (durata/num_frame).
FRAME_STRIDE_S = 0.02
