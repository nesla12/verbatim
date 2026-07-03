"""Orchestrazione della pipeline per un file audio.

Flusso: ffmpeg -> WAV 16k mono -> silero-VAD -> per segmento {letterale, leggibile}.
Streaming per-segmento: non si caricano mai i logit dell'intero file in RAM
(requisito file lunghi, 45 minuti). Output: un singolo JSON di progetto.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Callable, Optional

from config import PROJECTS_DIR, UPLOADS_DIR, TARGET_SR, LITERAL_MODEL_ID, READABLE_BACKEND
from app.pipeline import audio as audio_mod
from app.pipeline import vad as vad_mod
from app.pipeline import literal as literal_mod
from app.pipeline import readable as readable_mod

SCHEMA_VERSION = 2


def project_path(project_id: str) -> Path:
    return PROJECTS_DIR / f"{project_id}.json"


def migrate(project: dict) -> dict:
    """Porta un progetto vecchio allo schema corrente, in modo non distruttivo.

    v1 -> v2: aggiunge il campo 'speaker' (interlocutore) a ogni segmento e la lista
    'speakers' (etichette note) al progetto. Nessun dato esistente viene toccato.
    """
    if project.get("schema", 1) < 2:
        project.setdefault("speakers", [])
        for seg in project.get("segments", []):
            seg.setdefault("speaker", "")
        project["schema"] = SCHEMA_VERSION
    return project


def load_project(project_id: str) -> dict:
    return migrate(json.loads(project_path(project_id).read_text(encoding="utf-8")))


def save_project(project: dict) -> None:
    path = project_path(project["id"])
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_project(project_id: str) -> bool:
    """Elimina il JSON del progetto e il suo WAV. Azione attivata dall'insegnante."""
    jpath = project_path(project_id)
    if not jpath.exists():
        return False
    try:
        project = json.loads(jpath.read_text(encoding="utf-8"))
        wav = UPLOADS_DIR / project.get("audio", "")
        if wav.name and wav.exists():
            wav.unlink()
    except Exception:
        pass
    jpath.unlink(missing_ok=True)
    return True


def transcribe_file(
    src_path: str | Path,
    original_name: str | None = None,
    progress: Optional[Callable[[int, int], None]] = None,
    project_id: str | None = None,
) -> dict:
    """Trascrive un file e scrive il JSON di progetto. Ritorna il dict del progetto."""
    src_path = Path(src_path)
    project_id = project_id or uuid.uuid4().hex[:12]
    original_name = original_name or src_path.name

    # 1) normalizza in WAV 16k mono
    wav_path = UPLOADS_DIR / f"{project_id}.wav"
    audio_mod.to_wav_16k_mono(src_path, wav_path)
    samples, sr = audio_mod.load_wav(wav_path)
    assert sr == TARGET_SR, f"sample rate inatteso: {sr}"
    duration = round(len(samples) / sr, 3)

    # 2) segmenta
    segs = vad_mod.segment(samples, sr)
    total = len(segs)

    project = {
        "schema": SCHEMA_VERSION,
        "id": project_id,
        "name": original_name,
        "audio": wav_path.name,
        "duration": duration,
        "sr": sr,
        "literal_model": LITERAL_MODEL_ID,
        "readable_backend": READABLE_BACKEND,
        "status": "processing",
        "speakers": [],
        "segments": [],
    }
    save_project(project)

    # 3) per-segmento: letterale (con timestamp) + leggibile (riferimento)
    for i, seg in enumerate(segs):
        chunk = vad_mod.slice_audio(samples, seg["start"], seg["end"], sr)
        lit = literal_mod.transcribe_segment(chunk, sr)
        read = readable_mod.transcribe_segment(chunk, sr)

        # i timestamp di parola sono relativi al segmento -> li portiamo ad assoluti
        words = [
            {
                "w": w["w"],
                "start": round(seg["start"] + w["start"], 3),
                "end": round(seg["start"] + w["end"], 3),
            }
            for w in lit["words"]
        ]
        project["segments"].append(
            {
                "id": i,
                "start": seg["start"],
                "end": seg["end"],
                "literal": lit["text"],
                "words": words,
                "readable": read,
                "speaker": "",
            }
        )
        save_project(project)  # autosalvataggio incrementale
        if progress:
            progress(i + 1, total)

    project["status"] = "done"
    save_project(project)
    return project
