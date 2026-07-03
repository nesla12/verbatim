"""La migrazione di schema v1 -> v2 aggiunge i campi interlocutore senza rompere i dati."""
from app.pipeline import transcribe as pipe


def test_v1_migrates_to_v2():
    v1 = {
        "schema": 1, "id": "x", "name": "vecchio",
        "segments": [{"id": 0, "start": 0.0, "end": 1.0,
                      "literal": "ciao", "words": [], "readable": "ciao"}],
    }
    m = pipe.migrate(v1)
    assert m["schema"] == 2
    assert m["speakers"] == []
    assert m["segments"][0]["speaker"] == ""
    # il testo letterale NON deve essere toccato dalla migrazione
    assert m["segments"][0]["literal"] == "ciao"


def test_v2_is_left_intact():
    v2 = {
        "schema": 2, "id": "y", "name": "nuovo", "speakers": ["Bambino"],
        "segments": [{"id": 0, "start": 0, "end": 1, "literal": "a",
                      "words": [], "readable": "a", "speaker": "Bambino"}],
    }
    m = pipe.migrate(v2)
    assert m["speakers"] == ["Bambino"]
    assert m["segments"][0]["speaker"] == "Bambino"
