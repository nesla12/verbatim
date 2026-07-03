"""Diarizzazione: separa interlocutori, non tocca il testo letterale, gira offline."""
import socket

import pytest

from app.pipeline import diarize as diar
from app.pipeline import vad as vad_mod


def test_diarize_returns_one_label_per_segment(fixtures, load_wav):
    audio, sr = load_wav(fixtures["words"])
    segs = vad_mod.segment(audio, sr)
    labels = diar.diarize(audio, sr, segs, n_speakers=2)
    assert len(labels) == len(segs)
    assert all(isinstance(x, str) and x for x in labels)


def test_diarize_does_not_touch_literal(fixtures, load_wav):
    """La diarizzazione assegna solo etichette: non restituisce né modifica testo."""
    audio, sr = load_wav(fixtures["words"])
    segs = vad_mod.segment(audio, sr)
    # i segmenti passati a diarize hanno solo start/end: nessun campo testo coinvolto
    before = [dict(s) for s in segs]
    diar.diarize(audio, sr, segs, n_speakers=2)
    assert segs == before  # diarize non muta i segmenti in ingresso


def test_two_speakers_separated(fixtures, load_wav):
    if "two_speakers" not in fixtures:
        pytest.skip("meno di due voci SAPI disponibili sul sistema")
    audio, sr = load_wav(fixtures["two_speakers"])
    segs = vad_mod.segment(audio, sr)
    if len(segs) < 2:
        pytest.skip("la VAD non ha separato le due utterance")
    labels = diar.diarize(audio, sr, segs, n_speakers=2)
    assert len(set(labels)) == 2, f"attesi due interlocutori, ottenuti: {labels}"


def test_diarize_runs_offline(fixtures, load_wav, monkeypatch):
    diar._get_encoder()  # carica (pesi inclusi nel pacchetto, nessun download)
    real_connect = socket.socket.connect

    def guard(self, address):
        host = address[0] if isinstance(address, tuple) else ""
        if host not in ("127.0.0.1", "::1", "localhost", "0.0.0.0"):
            raise OSError("Rete bloccata durante la diarizzazione (test offline).")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guard)
    audio, sr = load_wav(fixtures["words"])
    segs = vad_mod.segment(audio, sr)
    labels = diar.diarize(audio, sr, segs, n_speakers=2)
    assert len(labels) == len(segs)
