"""TEST GATE — fedelta' sulle parole inventate.

Una clip con parole inventate deve uscire resa foneticamente nel livello letterale,
NON mappata su parole italiane reali. Verifichiamo che il testo letterale non contenga
la "correzione" da dizionario.
"""
import pytest

from app.pipeline import literal

# correzioni "plausibili" verso cui un modello con LM scivolerebbe
DICTIONARY_CORRECTIONS = ["meraviglioso", "strano", "stupendo", "bambino", "strampalato"]


def test_nonwords_stay_phonetic(fixtures, load_wav):
    audio, sr = load_wav(fixtures["nonword"])
    out = literal.transcribe_segment(audio, sr)
    text = out["text"].lower()

    assert text.strip(), "Il livello letterale non deve essere vuoto."
    for word in DICTIONARY_CORRECTIONS:
        assert word not in text, (
            f"Il livello letterale ha 'corretto' verso la parola di dizionario '{word}': "
            f"output = {text!r}. Le parole inventate devono restare fonetiche."
        )
