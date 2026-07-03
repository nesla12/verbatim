"""LIVELLO LETTERALE — wav2vec2 italiano, CTC greedy argmax PURO.

Vincolo NON negoziabile (DECISIONS.md D2 / CLAUDE.md):
- Wav2Vec2ForCTC + Wav2Vec2Processor (MAI Wav2Vec2ProcessorWithLM).
- decodifica greedy argmax sui logit, nessun language model, nessun kenlm.
- nessuna post-correzione (no LLM, no spellchecker).
- i timestamp per-parola derivano dagli indici di frame dell'allineamento CTC.

Questo e' il motivo per cui il tool esiste: scrive lettera per lettera cio' che sente.
"""
from __future__ import annotations

import numpy as np
import torch

from config import LITERAL_MODEL_ID, TARGET_SR

_processor = None
_model = None


def _load():
    global _processor, _model
    if _model is None:
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

        # Wav2Vec2Processor "nudo": NON Wav2Vec2ProcessorWithLM. Nessun decoder/kenlm.
        _processor = Wav2Vec2Processor.from_pretrained(LITERAL_MODEL_ID)
        _model = Wav2Vec2ForCTC.from_pretrained(LITERAL_MODEL_ID)
        _model.eval()
    return _processor, _model


def assert_no_language_model() -> None:
    """Guardia esplicita: il processor non deve avere un decoder LM/kenlm."""
    processor, _ = _load()
    from transformers import Wav2Vec2Processor

    if processor.__class__.__name__ != "Wav2Vec2Processor":
        raise AssertionError(
            f"Atteso Wav2Vec2Processor puro, trovato {processor.__class__.__name__}"
        )
    if getattr(processor, "decoder", None) is not None:
        raise AssertionError("Il processor ha un decoder LM: vietato per il livello letterale.")


def transcribe_segment(audio: np.ndarray, sr: int = TARGET_SR) -> dict:
    """Trascrive UN segmento. Ritorna {'text': str, 'words': [{'w','start','end'}]}.

    I timestamp sono relativi all'inizio del segmento (in secondi).
    """
    processor, model = _load()
    audio = np.asarray(audio, dtype=np.float32)
    if audio.size == 0:
        return {"text": "", "words": []}

    inputs = processor(audio, sampling_rate=sr, return_tensors="pt", padding=False)
    with torch.no_grad():
        logits = model(inputs.input_values).logits[0]  # [T, vocab]

    pred_ids = torch.argmax(logits, dim=-1).cpu().numpy()  # greedy argmax
    del logits  # non tratteniamo i logit (file lunghi: niente crescita RAM)

    num_frames = len(pred_ids)
    seg_dur = audio.shape[0] / sr
    # tempo per frame robusto: durata reale del segmento / numero di frame
    tpf = seg_dur / num_frames if num_frames else 0.0

    tok = processor.tokenizer
    blank_id = tok.pad_token_id
    delim_tok = getattr(tok, "word_delimiter_token", "|")
    delim_id = tok.convert_tokens_to_ids(delim_tok)

    words: list[dict] = []
    cur_chars: list[str] = []
    cur_start: int | None = None
    cur_end: int | None = None
    prev = -1

    def flush():
        nonlocal cur_chars, cur_start, cur_end
        if cur_chars and cur_start is not None:
            words.append(
                {
                    "w": "".join(cur_chars),
                    "start": round(cur_start * tpf, 3),
                    "end": round((cur_end + 1) * tpf, 3),
                }
            )
        cur_chars, cur_start, cur_end = [], None, None

    for t, p in enumerate(pred_ids):
        if p == prev:          # collassa ripetizioni CTC
            continue
        prev = p
        if p == blank_id:      # blank: separa emissioni
            continue
        if p == delim_id:      # confine di parola
            flush()
            continue
        ch = tok.convert_ids_to_tokens(int(p))
        if cur_start is None:
            cur_start = t
        cur_chars.append(ch)
        cur_end = t
    flush()

    text = " ".join(w["w"] for w in words).strip()
    return {"text": text, "words": words}
