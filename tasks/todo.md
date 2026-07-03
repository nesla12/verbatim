# Verbatim — MVP Build Plan

Local letter-faithful child-speech transcription (Italian). Pipeline + Italian UI + export.
Hard requirements from CLAUDE.md spec are NON-NEGOTIABLE (see DECISIONS.md).

## Phase 0 — Research & decisions (DONE)
- [x] Research parakeet-tdt-0.6b-v3 CPU install path (onnx-asr vs NeMo)
- [x] Confirm Python 3.12.6 / pip / ffmpeg 8.1.1 present on machine
- [x] Pin decision in DECISIONS.md (onnx-asr, fallback faster-whisper)

## Phase 1 — Scaffold
- [ ] Project tree: `app/`, `app/pipeline/`, `app/static/`, `tests/`, `tests/fixtures/`
- [ ] `requirements.txt` (fastapi, uvicorn, torch CPU, transformers, onnx-asr[cpu,hub], silero-vad, python-docx, soundfile, numpy)
- [ ] `config.py` — paths, model ids, READABLE_BACKEND switch, projects dir
- [ ] `README.md` (Italian quickstart) + `start.bat` launcher

## Phase 2 — Pipeline (the core)
- [ ] `audio.py` — ffmpeg ingest → 16 kHz mono WAV (clear Italian error if ffmpeg missing)
- [ ] `vad.py` — silero-vad segmentation into utterances (start/end seconds)
- [ ] `literal.py` — wav2vec2 CTC greedy argmax; word timestamps from CTC frame alignment; NO LM
- [ ] `readable.py` — onnx-asr parakeet v3 (fallback faster-whisper); reference-only label
- [ ] `transcribe.py` — orchestrate per-segment, stream (never hold full-file logits), write project JSON
- [ ] JSON schema: file meta + segments[{start,end,literal,words[{w,start,end}],readable}]

## Phase 3 — UI (Italian, FastAPI + vanilla JS)
- [ ] `main.py` FastAPI app: upload, list projects, get project JSON, autosave edits, export endpoints, audio serve
- [ ] `static/index.html` + `app.js` + `style.css`: drag&drop, per-file progress, segment list,
      audio player, click segment/word to play span, keyboard shortcuts (play/pause/replay segment),
      literal line editable (top, primary), readable line muted read-only (secondary), autosave
- [ ] Export `.txt` and `.docx` (literal text, optional timestamps, empty left speaker column)

## Phase 4 — Acceptance tests
- [ ] `test_nonword_fidelity.py` — invented words ("stranpolo", "merafiglioso") stay phonetic, NOT
      mapped to dictionary words (THE gate test)
- [ ] `test_offline.py` — transcription runs with network blocked (assert no outbound connections)
- [ ] `test_timestamps.py` — word N play offset within ±300 ms
- [ ] `test_no_lm.py` — assert literal path never instantiates ProcessorWithLM / loads kenlm
- [ ] Fixture generation (synthesize nonword clip via TTS or tone+record helper)

## Phase 5 — End-to-end run
- [ ] Install deps, download models once
- [ ] Run pipeline on a sample audio file → produce project JSON
- [ ] Launch UI, demonstrate review flow (edit a literal line, autosave)
- [ ] Export .docx
- [ ] Run nonword fidelity test → MUST pass before declaring done

## Review — COMPLETATO (2026-06-08)

**Tutte le fasi fatte.** MVP costruito end-to-end e verificato su file reale.

### Cosa è stato costruito
- **Pipeline** (`app/pipeline/`): ffmpeg → WAV 16k mono → silero-VAD → per-segmento
  wav2vec2 CTC greedy (LETTERALE, con timestamp di parola da allineamento CTC) +
  parakeet-v3 onnx (LEGGIBILE, solo riferimento). Streaming per-segmento, JSON incrementale.
- **UI italiana** (`app/main.py` + `app/static/`): drag&drop, progresso per file, lista
  segmenti, player audio, clic su segmento/parola = riproduzione dello span, scorciatoie
  (Spazio/R), letterale editabile in alto + leggibile muto sotto, autosalvataggio.
- **Export** `.txt` e `.docx` (colonna "Interlocutore" vuota, tempi opzionali).
- **Setup** `setup_models.py` (download una tantum, thread singolo per evitare la race symlink HF).

### Verifiche
- ✅ `pytest`: **5/5 passati** in 30 s.
- ✅ **GATE fedeltà parole inventate**: "stranpolo/merafiglioso/bimbalo" → letterale
  `strang- polo merafish liozo vimbado` (fonetico, NON corretto a parole reali).
- ✅ Garanzia **offline** (rete bloccata durante la trascrizione).
- ✅ Timestamp coerenti/monotoni; ✅ nessun language model nel livello letterale.
- ✅ Run e2e su `words.wav` → JSON prodotto + UI review verificata (endpoint 200, DOM corretto)
  + `.docx` valido generato.

### Decisioni chiave (vedi DECISIONS.md)
- READABLE = parakeet-tdt-0.6b-v3 via **onnx-asr** (no NeMo). Fallback faster-whisper via switch.
- Pin `torchaudio==2.9.0` per combaciare con torch 2.9.0 (silero importa torchaudio).

### Note operative
- Avvio: `start.bat` (apre il browser su :8000). Prima dell'uso: `python setup_models.py`.
- Richiede ffmpeg nel PATH (presente: 8.1.1). Nessun GPU richiesto.
