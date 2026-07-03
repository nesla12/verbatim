"""LIVELLO LEGGIBILE — solo riferimento (secondario).

Parakeet-tdt-0.6b-v3 via onnx-asr su CPU (DECISIONS.md D1), con fallback faster-whisper.
Questo livello NON produce timestamp e NON e' l'artefatto primario: serve solo come aiuto
di lettura accanto al testo letterale. Nessuna post-correzione del livello letterale.
"""
from __future__ import annotations

import numpy as np

from config import (
    READABLE_BACKEND,
    READABLE_ONNX_MODEL,
    READABLE_WHISPER_MODEL,
    TARGET_SR,
)

_model = None
_backend = None


def _load():
    global _model, _backend
    if _model is not None:
        return _model, _backend

    if READABLE_BACKEND == "onnx":
        import onnx_asr

        _model = onnx_asr.load_model(READABLE_ONNX_MODEL)
        _backend = "onnx"
    elif READABLE_BACKEND == "faster-whisper":
        from faster_whisper import WhisperModel

        _model = WhisperModel(READABLE_WHISPER_MODEL, device="cpu", compute_type="int8")
        _backend = "faster-whisper"
    else:
        raise ValueError(f"READABLE_BACKEND sconosciuto: {READABLE_BACKEND}")
    return _model, _backend


def transcribe_segment(audio: np.ndarray, sr: int = TARGET_SR) -> str:
    """Trascrizione leggibile di un segmento. Ritorna solo testo (nessun timestamp)."""
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0:
        return ""
    model, backend = _load()

    if backend == "onnx":
        # onnx-asr accetta un waveform numpy float32 + sample_rate; lingua auto (v3).
        result = model.recognize(audio, sample_rate=sr)
        return (result or "").strip()

    # faster-whisper: temperature 0, niente condizionamento sul testo precedente,
    # nessuna post-elaborazione. Esplicitamente "solo riferimento".
    segments, _ = model.transcribe(
        audio,
        language="it",
        temperature=0.0,
        condition_on_previous_text=False,
        beam_size=1,
    )
    return " ".join(s.text.strip() for s in segments).strip()
