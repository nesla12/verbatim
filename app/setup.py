"""Stato e download dei modelli (una tantum), condiviso da CLI e UI di primo avvio.

I modelli vengono scaricati una sola volta (serve connessione), poi tutto è offline.
silero-vad e resemblyzer hanno i pesi inclusi nel pacchetto: nessun download.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import config  # noqa: F401  (imposta HF_HUB_DISABLE_SYMLINKS_WARNING / HF_HOME)
from config import LITERAL_MODEL_ID, READABLE_BACKEND, READABLE_ONNX_MODEL

READABLE_REPO = "istupakov/parakeet-tdt-0.6b-v3-onnx"


def _repo_cached(repo_id: str) -> bool:
    from huggingface_hub import constants

    cache = Path(constants.HF_HUB_CACHE)
    d = cache / ("models--" + repo_id.replace("/", "--"))
    snaps = d / "snapshots"
    return snaps.exists() and any(snaps.glob("*/*"))


def model_status() -> dict:
    """Quali modelli mancano dalla cache locale."""
    missing = []
    if not _repo_cached(LITERAL_MODEL_ID):
        missing.append("trascrizione letterale")
    if READABLE_BACKEND == "onnx" and not _repo_cached(READABLE_REPO):
        missing.append("trascrizione di riferimento")
    return {"ready": not missing, "missing": missing}


def download_all(progress: Optional[Callable[[str], None]] = None) -> None:
    """Scarica/verifica tutti i modelli (thread singolo: evita la race symlink di HF)."""
    def step(msg: str):
        if progress:
            progress(msg)

    step("Modello letterale (wav2vec2 italiano)…")
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

    Wav2Vec2Processor.from_pretrained(LITERAL_MODEL_ID)
    Wav2Vec2ForCTC.from_pretrained(LITERAL_MODEL_ID)

    step("Modello di segmentazione (VAD)…")
    from silero_vad import load_silero_vad

    load_silero_vad()

    if READABLE_BACKEND == "onnx":
        step("Modello di riferimento (parakeet)…")
        from huggingface_hub import snapshot_download

        snapshot_download(READABLE_REPO, max_workers=1)  # thread singolo
        import onnx_asr

        onnx_asr.load_model(READABLE_ONNX_MODEL)

    step("Modello interlocutori (resemblyzer)…")
    from resemblyzer import VoiceEncoder

    VoiceEncoder(verbose=False)  # pesi inclusi: nessun download

    step("Completato.")
