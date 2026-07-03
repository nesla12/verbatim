"""Segmentazione in utterance con silero-vad.

silero-vad e' impacchettato col pip package: load_silero_vad() carica un modello locale,
nessuna rete. Produciamo segmenti brevi (unita' naturali di editing), con un tetto duro
di durata per restare nel range ottimale di wav2vec2 e parakeet.
"""
from __future__ import annotations

import numpy as np
import torch

from config import TARGET_SR, VAD_MIN_SILENCE_MS, VAD_MIN_SPEECH_MS, VAD_MAX_SEGMENT_S

_model = None


def _get_model():
    global _model
    if _model is None:
        from silero_vad import load_silero_vad
        _model = load_silero_vad()
    return _model


def _split_long(start: float, end: float, max_s: float):
    """Spezza un segmento troppo lungo in pezzi uguali <= max_s."""
    dur = end - start
    if dur <= max_s:
        yield start, end
        return
    n = int(np.ceil(dur / max_s))
    step = dur / n
    for i in range(n):
        s = start + i * step
        yield s, min(s + step, end)


def segment(audio: np.ndarray, sr: int = TARGET_SR) -> list[dict]:
    """Ritorna una lista di segmenti {'start': s, 'end': s} in secondi."""
    from silero_vad import get_speech_timestamps

    model = _get_model()
    wav = torch.from_numpy(np.asarray(audio, dtype=np.float32))
    ts = get_speech_timestamps(
        wav,
        model,
        sampling_rate=sr,
        min_silence_duration_ms=VAD_MIN_SILENCE_MS,
        min_speech_duration_ms=VAD_MIN_SPEECH_MS,
        return_seconds=True,
    )
    segments: list[dict] = []
    for t in ts:
        for s, e in _split_long(float(t["start"]), float(t["end"]), VAD_MAX_SEGMENT_S):
            segments.append({"start": round(s, 3), "end": round(e, 3)})
    # fallback: se la VAD non trova nulla, tratta tutto come un singolo segmento spezzato
    if not segments and len(audio) > 0:
        total = len(audio) / sr
        for s, e in _split_long(0.0, total, VAD_MAX_SEGMENT_S):
            segments.append({"start": round(s, 3), "end": round(e, 3)})
    return segments


def slice_audio(audio: np.ndarray, start: float, end: float, sr: int = TARGET_SR) -> np.ndarray:
    a = max(0, int(start * sr))
    b = min(len(audio), int(end * sr))
    return audio[a:b]
