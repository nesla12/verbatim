"""API della libreria progetti: elenco, rinomina, elimina, riconciliazione orfani."""
import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.pipeline import transcribe as pipe

client = TestClient(main.app)


def _fake_project(pid: str, status: str = "done") -> dict:
    return {
        "schema": 2, "id": pid, "name": "originale", "audio": f"{pid}.wav",
        "duration": 1.0, "sr": 16000, "status": status, "speakers": [],
        "segments": [{"id": 0, "start": 0, "end": 1, "literal": "ciao",
                      "words": [], "readable": "ciao", "speaker": ""}],
    }


def test_list_rename_delete():
    pid = "testlib0001"
    pipe.save_project(_fake_project(pid))
    try:
        ids = [p["id"] for p in client.get("/api/projects").json()]
        assert pid in ids

        r = client.patch(f"/api/project/{pid}", json={"name": "rinominato"})
        assert r.status_code == 200 and r.json()["name"] == "rinominato"
        assert pipe.load_project(pid)["name"] == "rinominato"

        # nome vuoto rifiutato
        assert client.patch(f"/api/project/{pid}", json={"name": "  "}).status_code == 400

        r = client.delete(f"/api/project/{pid}")
        assert r.status_code == 200 and r.json()["ok"] is True
        assert not pipe.project_path(pid).exists()
    finally:
        pipe.project_path(pid).unlink(missing_ok=True)


def test_reconcile_orphan_on_startup():
    pid = "testorphan02"
    pipe.save_project(_fake_project(pid, status="processing"))
    try:
        main._reconcile_orphans()
        assert pipe.load_project(pid)["status"] == "interrupted"
    finally:
        pipe.project_path(pid).unlink(missing_ok=True)


def test_speaker_edit_and_rename():
    pid = "testspk0003"
    pipe.save_project(_fake_project(pid))
    try:
        # assegna interlocutore a un segmento -> entra nella lista speakers
        r = client.put(f"/api/project/{pid}/segment/0", json={"speaker": "Interlocutore 1"})
        assert "Interlocutore 1" in r.json()["speakers"]
        # il testo letterale resta invariato
        assert pipe.load_project(pid)["segments"][0]["literal"] == "ciao"

        # rinomina globale
        r = client.post(f"/api/project/{pid}/speaker/rename",
                        json={"old": "Interlocutore 1", "new": "Bambino"})
        assert r.json()["speakers"] == ["Bambino"]
        assert pipe.load_project(pid)["segments"][0]["speaker"] == "Bambino"
    finally:
        pipe.project_path(pid).unlink(missing_ok=True)
