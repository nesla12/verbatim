"""Sintesi locale (offline) delle clip di test via TTS Windows SAPI5 (pyttsx3).

Le clip vengono poi normalizzate a WAV 16 kHz mono con la stessa pipeline di ingest.
Nessuna rete: SAPI5 e' integrato in Windows.
"""
from __future__ import annotations

from pathlib import Path

from app.pipeline import audio as audio_mod

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)

# parole inventate (devono restare foneticamente fedeli, NON "corrette")
NONWORD_TEXT = "stranpolo. merafiglioso. bimbalo."
# parole reali e chiare per il test dei timestamp
WORDS_TEXT = "il gatto mangia la mela rossa."


def _tts(text: str, dst: Path) -> Path:
    import pyttsx3

    raw = dst.with_suffix(".raw.wav")
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.save_to_file(text, str(raw))
    engine.runAndWait()
    engine.stop()
    # normalizza a 16 kHz mono come tutto il resto della pipeline
    audio_mod.to_wav_16k_mono(raw, dst)
    raw.unlink(missing_ok=True)
    return dst


def _two_speaker(dst: Path, words_path: Path) -> Path:
    """Genera una clip con DUE timbri diversi separati da una pausa.

    Per testare la diarizzazione servono due voci acusticamente distinte. Senza ricorrere a
    una seconda voce SAPI (pyttsx3 si blocca riusando il driver), creiamo il secondo
    "interlocutore" abbassando di molto il pitch della clip esistente: il timbro cambia
    abbastanza da essere assegnato a un cluster diverso.
    """
    import librosa
    import numpy as np
    import soundfile as sf

    from config import TARGET_SR
    from app.pipeline import audio as audio_mod

    spk_a, _ = audio_mod.load_wav(words_path)
    spk_b = librosa.effects.pitch_shift(spk_a, sr=TARGET_SR, n_steps=-7)  # voce più grave
    gap = np.zeros(int(0.6 * TARGET_SR), dtype="float32")
    combined = np.concatenate([spk_a, gap, spk_b]).astype("float32")
    sf.write(str(dst), combined, TARGET_SR, subtype="PCM_16")
    return dst


def ensure_fixtures() -> dict[str, Path]:
    nonword = FIXTURES / "nonword.wav"
    words = FIXTURES / "words.wav"
    if not nonword.exists():
        _tts(NONWORD_TEXT, nonword)
    if not words.exists():
        _tts(WORDS_TEXT, words)
    out = {"nonword": nonword, "words": words}

    two = FIXTURES / "two_speakers.wav"
    if not two.exists():
        _two_speaker(two, words)
    out["two_speakers"] = two
    return out


if __name__ == "__main__":
    paths = ensure_fixtures()
    for k, v in paths.items():
        print(f"{k}: {v}")
