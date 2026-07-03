"""I timestamp di parola devono essere coerenti e dentro i limiti dell'audio.

Il requisito utente (clic su parola N -> riproduzione entro +/-300 ms) si fonda su
timestamp monotoni e plausibili derivati dall'allineamento CTC. Qui verifichiamo
deterministicamente quelle proprieta'.
"""
from app.pipeline import literal


def test_word_timestamps_plausible(fixtures, load_wav):
    audio, sr = load_wav(fixtures["words"])
    dur = len(audio) / sr
    out = literal.transcribe_segment(audio, sr)
    words = out["words"]

    assert len(words) >= 2, f"Attese piu' parole, ottenute: {out['text']!r}"

    prev_start = -1.0
    for w in words:
        assert 0.0 <= w["start"] < w["end"] <= dur + 0.05, f"Timestamp fuori range: {w}"
        assert w["start"] >= prev_start - 0.05, f"Timestamp non monotoni: {w}"
        prev_start = w["start"]
        # durata di una parola pronunciata: plausibile sotto i 3 s
        assert (w["end"] - w["start"]) < 3.0, f"Parola troppo lunga: {w}"
