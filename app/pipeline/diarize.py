"""Diarizzazione: chi parla in ogni segmento (automatica, offline, non gated).

Approccio: per ogni segmento della VAD calcoliamo un'impronta vocale (d-vector) con
Resemblyzer — i cui pesi sono inclusi nel pacchetto pip, quindi NESSUN download e
funzionamento offline garantito — e raggruppiamo i segmenti per somiglianza
(clustering agglomerativo, distanza coseno).

La diarizzazione PROPONE le etichette; l'insegnante le corregge e rinomina nella UI.
Non tocca MAI il testo letterale: assegna solo 'speaker' a ciascun segmento.
"""
from __future__ import annotations

import numpy as np

from config import TARGET_SR

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        from resemblyzer import VoiceEncoder

        _encoder = VoiceEncoder(verbose=False)  # pesi inclusi nel pacchetto, niente rete
    return _encoder


def _embeddings(samples: np.ndarray, sr: int, segments: list[dict], progress=None):
    from resemblyzer import preprocess_wav

    enc = _get_encoder()
    embs: list[np.ndarray | None] = []
    for i, seg in enumerate(segments):
        a = max(0, int(seg["start"] * sr))
        b = min(len(samples), int(seg["end"] * sr))
        chunk = samples[a:b]
        emb = None
        try:
            wav = preprocess_wav(chunk, source_sr=sr)
            if len(wav) >= int(0.4 * TARGET_SR):  # troppo corto -> impronta inaffidabile
                emb = enc.embed_utterance(wav)
        except Exception:
            emb = None
        embs.append(emb)
        if progress:
            progress(i + 1, len(segments))
    return embs


def _order_by_first_appearance(cluster_ids: list[int]) -> dict[int, int]:
    """Rinumera i cluster nell'ordine in cui compaiono (chi parla prima = Interlocutore 1)."""
    mapping: dict[int, int] = {}
    nxt = 1
    for c in cluster_ids:
        if c not in mapping:
            mapping[c] = nxt
            nxt += 1
    return mapping


def diarize(samples: np.ndarray, sr: int, segments: list[dict],
            n_speakers: int = 2, progress=None) -> list[str]:
    """Ritorna una lista di etichette ('Interlocutore 1', ...) allineata ai segmenti."""
    if not segments:
        return []

    embs = _embeddings(samples, sr, segments, progress=progress)
    valid = [(i, e) for i, e in enumerate(embs) if e is not None]

    # casi limite: nessuna impronta o un solo parlante richiesto
    if len(valid) <= 1 or n_speakers <= 1:
        return ["Interlocutore 1"] * len(segments)

    from sklearn.cluster import AgglomerativeClustering

    X = np.vstack([e for _, e in valid])
    k = min(n_speakers, len(valid))
    cluster = AgglomerativeClustering(n_clusters=k, metric="cosine", linkage="average")
    raw = cluster.fit_predict(X).tolist()

    remap = _order_by_first_appearance(raw)
    valid_labels = {idx: f"Interlocutore {remap[c]}" for (idx, _), c in zip(valid, raw)}

    # i segmenti senza impronta ereditano l'etichetta del precedente valido (continuità)
    labels: list[str] = []
    last = "Interlocutore 1"
    for i in range(len(segments)):
        if i in valid_labels:
            last = valid_labels[i]
        labels.append(last)
    return labels
