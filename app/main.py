"""Verbatim — applicazione web locale (FastAPI + pagina statica).

Una sola finestra: libreria dei progetti, drag & drop, revisione (lettore audio, modifica
del testo letterale, etichette interlocutore), autosalvataggio, esportazione .txt / .docx.
Tutto in italiano, nessun terminale. Utente singolo, completamente offline.
"""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

import config
from config import UPLOADS_DIR, PROJECTS_DIR
from app.pipeline import transcribe as pipe
from app import export as export_mod

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Verbatim")

# stato di avanzamento in memoria: id -> {"done", "total", "status", "phase", "error"}
_progress: dict[str, dict] = {}


def _reconcile_orphans() -> None:
    """All'avvio: i progetti rimasti 'processing' (per crash/chiusura) diventano 'interrupted'.

    Così la libreria mostra lo stato reale dopo un riavvio invece di un avanzamento fantasma.
    """
    for p in PROJECTS_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("status") == "processing":
                d["status"] = "interrupted"
                p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            continue


_reconcile_orphans()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


# ============================================================================
# Informazioni app + accettazione disclaimer legale (una tantum)
# ============================================================================
@app.get("/api/info")
def app_info() -> dict:
    """Metadati mostrati in 'Informazioni', nella home e per la validazione dei formati."""
    return {
        "version": config.APP_VERSION,
        "author": config.APP_AUTHOR,
        "site": config.APP_SITE,
        "repo": config.APP_REPO,
        "audio_exts": config.AUDIO_EXTS,
        "video_exts": config.VIDEO_EXTS,
        "max_minutes": config.MAX_RECOMMENDED_MINUTES,
        "accepted": config.LEGAL_ACCEPTED_FILE.exists(),
    }


@app.post("/api/legal/accept")
def legal_accept() -> dict:
    """Registra l'accettazione del disclaimer scrivendo un marcatore locale."""
    try:
        config.LEGAL_ACCEPTED_FILE.write_text(
            f"accepted v{config.APP_VERSION}\n", encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"Impossibile salvare l'accettazione: {e}")
    return {"ok": True}


# ============================================================================
# Primo avvio: download modelli (una tantum)
# ============================================================================
_setup_state: dict = {"running": False, "phase": "", "error": None}


@app.get("/api/setup/status")
def setup_status() -> dict:
    from app.setup import model_status

    return {**model_status(), **_setup_state}


@app.post("/api/setup/download")
def setup_download() -> dict:
    if _setup_state["running"]:
        return {"ok": True}
    _setup_state.update(running=True, phase="Avvio…", error=None)

    def _run():
        try:
            from app.setup import download_all

            download_all(progress=lambda m: _setup_state.update(phase=m))
            _setup_state.update(running=False, phase="Completato.")
        except Exception as e:  # noqa: BLE001
            _setup_state.update(running=False, error=str(e))

    threading.Thread(target=_run, daemon=True).start()
    return {"ok": True}


# ============================================================================
# Libreria progetti
# ============================================================================
@app.get("/api/projects")
def list_projects() -> list[dict]:
    out = []
    for p in PROJECTS_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({
                "id": d["id"],
                "name": d.get("name"),
                "status": d.get("status"),
                "duration": d.get("duration"),
                "n_segments": len(d.get("segments", [])),
                "speakers": d.get("speakers", []),
                "created": p.stat().st_mtime,
            })
        except Exception:
            continue
    out.sort(key=lambda x: x["created"], reverse=True)  # più recenti in alto
    return out


@app.patch("/api/project/{project_id}")
async def rename_project(project_id: str, payload: dict) -> dict:
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(400, "Il nome non può essere vuoto.")
    project = pipe.load_project(project_id)
    project["name"] = name
    pipe.save_project(project)
    return {"ok": True, "name": name}


@app.delete("/api/project/{project_id}")
def remove_project(project_id: str) -> dict:
    if not pipe.delete_project(project_id):
        raise HTTPException(404, "Progetto non trovato")
    _progress.pop(project_id, None)
    return {"ok": True}


# ============================================================================
# Caricamento + trascrizione
# ============================================================================
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> JSONResponse:
    pid = uuid.uuid4().hex[:12]
    raw = UPLOADS_DIR / f"{pid}_src_{file.filename}"
    with open(raw, "wb") as f:
        f.write(await file.read())

    _progress[pid] = {"done": 0, "total": 0, "status": "processing", "phase": "transcribe"}

    def _run():
        try:
            def cb(done, total):
                _progress[pid] = {"done": done, "total": total,
                                  "status": "processing", "phase": "transcribe"}

            pipe.transcribe_file(raw, original_name=file.filename, progress=cb, project_id=pid)
            cur = _progress.get(pid, {})
            _progress[pid] = {"done": cur.get("total", 0), "total": cur.get("total", 0),
                              "status": "done", "phase": "transcribe"}
        except Exception as e:  # noqa: BLE001
            _progress[pid] = {"done": 0, "total": 0, "status": "error", "error": str(e)}
        finally:
            try:
                raw.unlink(missing_ok=True)
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"id": pid})


@app.get("/api/progress/{project_id}")
def progress(project_id: str) -> dict:
    if project_id in _progress:
        return _progress[project_id]
    # non in memoria (riavvio app): ripiega sullo stato salvato nel JSON
    path = pipe.project_path(project_id)
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            return {"status": d.get("status", "unknown"),
                    "done": len(d.get("segments", [])),
                    "total": len(d.get("segments", []))}
        except Exception:
            pass
    return {"status": "unknown"}


# ============================================================================
# Lettura / modifica progetto
# ============================================================================
@app.get("/api/project/{project_id}")
def get_project(project_id: str) -> dict:
    path = pipe.project_path(project_id)
    if not path.exists():
        raise HTTPException(404, "Progetto non trovato")
    return pipe.load_project(project_id)


@app.put("/api/project/{project_id}/segment/{seg_id}")
async def update_segment(project_id: str, seg_id: int, payload: dict) -> dict:
    """Autosalvataggio: testo letterale e/o etichetta interlocutore di un segmento."""
    project = pipe.load_project(project_id)
    for seg in project["segments"]:
        if seg["id"] == seg_id:
            if "literal" in payload:
                seg["literal"] = payload["literal"]
            if "speaker" in payload:
                spk = (payload["speaker"] or "").strip()
                seg["speaker"] = spk
                if spk and spk not in project.get("speakers", []):
                    project.setdefault("speakers", []).append(spk)
            break
    else:
        raise HTTPException(404, "Segmento non trovato")
    pipe.save_project(project)
    return {"ok": True, "speakers": project.get("speakers", [])}


@app.post("/api/project/{project_id}/diarize")
def diarize_project(project_id: str, payload: dict | None = None) -> JSONResponse:
    """Avvia la diarizzazione automatica (in background). Proporne le etichette interlocutore."""
    path = pipe.project_path(project_id)
    if not path.exists():
        raise HTTPException(404, "Progetto non trovato")
    n_speakers = int((payload or {}).get("n_speakers", 2))
    _progress[project_id] = {"done": 0, "total": 0, "status": "processing", "phase": "diarize"}

    def _run():
        try:
            from app.pipeline import audio as audio_mod
            from app.pipeline import diarize as diar_mod

            project = pipe.load_project(project_id)
            wav = UPLOADS_DIR / project["audio"]
            samples, sr = audio_mod.load_wav(wav)

            def cb(done, total):
                _progress[project_id] = {"done": done, "total": total,
                                         "status": "processing", "phase": "diarize"}

            labels = diar_mod.diarize(samples, sr, project["segments"],
                                      n_speakers=n_speakers, progress=cb)
            seen: list[str] = []
            for seg, lab in zip(project["segments"], labels):
                seg["speaker"] = lab
                if lab not in seen:
                    seen.append(lab)
            project["speakers"] = seen
            pipe.save_project(project)
            _progress[project_id] = {"done": len(labels), "total": len(labels),
                                     "status": "done", "phase": "diarize"}
        except Exception as e:  # noqa: BLE001
            _progress[project_id] = {"status": "error", "phase": "diarize", "error": str(e)}

    threading.Thread(target=_run, daemon=True).start()
    return JSONResponse({"ok": True})


@app.post("/api/project/{project_id}/speaker/rename")
async def rename_speaker(project_id: str, payload: dict) -> dict:
    """Rinomina un interlocutore ovunque compaia (es. 'Interlocutore 1' -> 'Bambino')."""
    old = (payload.get("old") or "").strip()
    new = (payload.get("new") or "").strip()
    if not new:
        raise HTTPException(400, "Il nome non può essere vuoto.")
    project = pipe.load_project(project_id)
    for seg in project["segments"]:
        if seg.get("speaker", "") == old:
            seg["speaker"] = new
    speakers = [new if s == old else s for s in project.get("speakers", [])]
    # dedup mantenendo l'ordine
    project["speakers"] = list(dict.fromkeys(speakers))
    pipe.save_project(project)
    return {"ok": True, "speakers": project["speakers"]}


# ============================================================================
# Audio + esportazione
# ============================================================================
@app.get("/api/audio/{project_id}")
def audio(project_id: str):
    project = pipe.load_project(project_id)
    wav = UPLOADS_DIR / project["audio"]
    if not wav.exists():
        raise HTTPException(404, "Audio non trovato")
    return FileResponse(wav, media_type="audio/wav")


@app.get("/api/export/{project_id}.txt")
def export_txt(project_id: str, timestamps: bool = False):
    project = pipe.load_project(project_id)
    text = export_mod.to_txt(project, with_timestamps=timestamps)
    fname = f"{project.get('name', project_id)}.txt"
    return Response(
        content=text.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.get("/api/export/{project_id}.docx")
def export_docx(project_id: str, timestamps: bool = False):
    project = pipe.load_project(project_id)
    data = export_mod.to_docx_bytes(project, with_timestamps=timestamps)
    fname = f"{project.get('name', project_id)}.docx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
