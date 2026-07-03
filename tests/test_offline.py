"""Garanzia offline: la trascrizione di una fixture gira con la rete bloccata.

Strategia: si pre-carica il modello (eventuale download avviene una sola volta in setup),
poi si installa una guardia che blocca QUALSIASI connessione socket non-loopback e si
esegue la trascrizione. Se venisse tentata una connessione di rete il test fallisce.
"""
import socket

import pytest

from app.pipeline import literal

_real_connect = socket.socket.connect
_real_create = socket.create_connection


def _is_local(address):
    try:
        host = address[0]
    except Exception:
        return False
    return host in ("127.0.0.1", "::1", "localhost", "0.0.0.0")


def test_transcription_runs_offline(fixtures, load_wav, monkeypatch):
    # pre-carica i modelli PRIMA del blocco (download una tantum consentito in setup)
    literal._load()

    attempts = []

    def guard_connect(self, address):
        if not _is_local(address):
            attempts.append(address)
            raise OSError("Connessione di rete bloccata durante la trascrizione (test offline).")
        return _real_connect(self, address)

    def guard_create(address, *a, **k):
        if not _is_local(address):
            attempts.append(address)
            raise OSError("Connessione di rete bloccata durante la trascrizione (test offline).")
        return _real_create(address, *a, **k)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)
    monkeypatch.setattr(socket, "create_connection", guard_create)

    audio, sr = load_wav(fixtures["nonword"])
    out = literal.transcribe_segment(audio, sr)

    assert out["text"] is not None
    assert not attempts, f"Tentativi di rete durante la trascrizione: {attempts}"
