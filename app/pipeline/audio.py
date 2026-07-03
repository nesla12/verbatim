"""Ingest audio -> WAV 16 kHz mono via ffmpeg.

Accetta qualsiasi formato comune (wav/mp3/m4a/ogg) e anche tracce audio da video.
Se ffmpeg non e' installato, solleva un errore in italiano chiaro per l'utente.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

from config import TARGET_SR


class FFmpegMancante(RuntimeError):
    pass


def _bundled_ffmpeg() -> str | None:
    """Cerca un ffmpeg.exe distribuito accanto all'app (per la versione impacchettata)."""
    roots = []
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).parent)        # cartella dell'eseguibile
    roots.append(Path(__file__).resolve().parents[2])    # cartella del progetto (dev)
    for root in roots:
        for cand in (root / "ffmpeg.exe", root / "ffmpeg" / "bin" / "ffmpeg.exe",
                     root / "ffmpeg" / "ffmpeg.exe"):
            if cand.exists():
                return str(cand)
    return None


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg") or _bundled_ffmpeg()
    if not exe:
        raise FFmpegMancante(
            "ffmpeg non e' stato trovato sul computer. "
            "Installa ffmpeg e assicurati che sia nel PATH, poi riavvia il programma."
        )
    return exe


def to_wav_16k_mono(src: str | Path, dst: str | Path) -> Path:
    """Converte qualunque file audio/video in WAV PCM 16-bit, 16 kHz, mono."""
    exe = _ffmpeg()
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        exe, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-ac", "1", "-ar", str(TARGET_SR),
        "-c:a", "pcm_s16le",
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Conversione audio fallita per '{src.name}'. "
            f"Il file potrebbe essere danneggiato o in un formato non supportato.\n"
            f"Dettagli ffmpeg: {proc.stderr.strip()}"
        )
    return dst


def load_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Carica un WAV gia' normalizzato come float32 mono in [-1, 1]."""
    data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data, sr
