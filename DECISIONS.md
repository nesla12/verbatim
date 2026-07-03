# DECISIONS

Architectural decisions for **Verbatim** — local letter-faithful child-speech transcription (Italian).
Each entry is pinned with the reason so it is not silently re-litigated later.

---

## D1 — Readable layer ASR runtime: `onnx-asr` (NOT full NeMo)

**Date:** 2026-06-08
**Choice:** Use `nvidia/parakeet-tdt-0.6b-v3` through the **`onnx-asr`** package on CPU, loaded as
`onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3")`.

**Install:** `pip install onnx-asr[cpu,hub]`

**Reason:**
- The end machine is a normal Windows laptop **without GPU**. The full NeMo toolkit pulls in a very
  heavy dependency tree (PyTorch Lightning, hydra, large CUDA-oriented stack, frequent Windows build
  pain) that is overkill for inference-only CPU use.
- `onnx-asr` is a lightweight ONNX Runtime wrapper that explicitly supports **Parakeet v3
  (multilingual)** and runs "from small IoT/edge devices to servers". CPU inference is a first-class
  target. Model weights download once from the HF hub, then run offline.
- Verified at build time (2026-06-08): the HF model card confirms `parakeet-tdt-0.6b-v3` supports
  **Italian** with **automatic language identification** (no prompt/lang flag needed), across 25 EU
  languages. Max usable chunk ~20–30 s, which matches our VAD-segmented pipeline.

**Fallback (pinned):** If the ONNX route proves unreliable on the target machine (model download,
ORT op support, or accuracy), fall back to **`faster-whisper large-v3`** with `temperature=0`,
`condition_on_previous_text=False`, no post-processing — and label it **reference-only** in the UI.
The fallback is selected by a single config switch (`READABLE_BACKEND` in `config.py`); the rest of
the pipeline is backend-agnostic because the readable layer never produces timestamps (those come
only from the literal layer).

**Rejected:** Full `nemo_toolkit[asr]` — heavyweight, GPU-oriented, fragile on Windows CPU laptops.

---

## D2 — Literal layer is FIXED by hard requirement (no decision latitude)

`jonatasgrosman/wav2vec2-large-xlsr-53-italian` via `Wav2Vec2ForCTC` + `Wav2Vec2Processor`,
**greedy argmax CTC**, no LM. Never `Wav2Vec2ProcessorWithLM`, never kenlm, never LLM/spellcheck
post-correction. Word timestamps are derived from CTC frame indices. This is the product's reason to
exist and is not subject to change.

---

## D3 — Segmentation: `silero-vad`

Short utterance segments (natural editing units). wav2vec2 performs best on short chunks, and Parakeet
v3 wants <30 s chunks — VAD satisfies both. Logits are processed per-segment and never accumulated for
the whole file (memory requirement for 45-min files).

---

## D4 — UI: FastAPI + single static HTML/JS page, no build step

Italian UI, one window, drag & drop, segment list with audio player, two text lines per segment
(literal editable on top, readable muted read-only below), autosave to project JSON, export to
.txt/.docx. No bundler, no node toolchain — vanilla JS served by FastAPI/uvicorn.

---

## D5 — Project state: plain JSON files (no SQLite for MVP)

One JSON per audio file is the single source of truth and the export source. Simpler than SQLite for a
single-user local tool; trivially inspectable. Revisit only if multi-project indexing is needed.

Schema v2 (production) adds a `speaker` field per segment and a `speakers` list per project.
`load_project` migrates v1→v2 in memory (non-destructive); existing projects keep working.

---

## D6 — Speaker diarization: Resemblyzer (NOT pyannote / SpeechBrain)

**Date:** 2026-06-11
**Choice:** Per-segment speaker embeddings via **Resemblyzer** (`VoiceEncoder`) + agglomerative
clustering (`scikit-learn`, cosine distance), default 2 speakers. Diarization PROPOSES labels;
the teacher corrects/renames them in the UI. It never touches the literal text.

**Reason:**
- **Offline hard requirement.** Resemblyzer ships its pretrained weights *inside the pip package*
  (`pretrained.pt`) → **zero model download**, works offline out of the box. Perfect fit.
- **pyannote** pretrained pipeline is **license-gated** (HF token + accept terms) → violates the
  "no friction / offline" goal. Rejected.
- **SpeechBrain ECAPA** is non-gated but downloads an ~80 MB model and has heavier Windows quirks
  (savedir symlinks). Resemblyzer avoids the download entirely.

**Gotcha (pinned):** Resemblyzer depends on `webrtcvad`, which has **no Python 3.12 wheel** and
needs a C compiler. Fix: install **`webrtcvad-wheels`** (drop-in, prebuilt) and install
`resemblyzer --no-deps` (see `install.bat`). Diarization itself never calls webrtcvad in our path
(we feed pre-segmented VAD chunks).

**Accuracy note:** diarization on child speech is imperfect by nature. It is a *proposal*; the UI
makes manual correction the primary affordance. Default n_speakers=2 (child + interviewer).

---

## D7 — Packaging: PyInstaller (onedir) + first-run model download

**Date:** 2026-07-03 (rivisto)
**Choice (FINALE):** distribuzione tramite **Python embeddable portable + installer Inno Setup**.
`build/build_portable.ps1` crea una cartella con il Python ufficiale embeddable, tutte le
dipendenze pre-installate, ffmpeg statico e `Verbatim.bat`; `installer/verbatim.iss` la impacchetta
in `Verbatim-Setup.exe` con collegamenti Desktop/menu. I modelli NON sono inclusi: al primo avvio
l'app li scarica una volta in `%LOCALAPPDATA%\Verbatim\models`, poi offline.

**Perché NON PyInstaller (approccio scartato):**
- Impacchettare torch + transformers con PyInstaller si è rivelato **inutilizzabile**: la fase di
  analisi con `collect_all()` su questi pacchetti girava da **8 ore senza finire** (esplosione
  combinatoria dei moduli + Windows Defender che scandisce ogni file).
- Il Python embeddable con dipendenze pre-installate è l'approccio standard e affidabile per app
  ML in Python: nessuna analisi pesante, ambiente vero e testabile.

**Gotcha critico (pinned):** il Python embeddable con `import site` attivo vede i pacchetti globali
in `%APPDATA%\Python` → pip li considera "già soddisfatti" e lascia la cartella VUOTA (funziona
solo sulla macchina di build!). Fix OBBLIGATORIO: `PYTHONNOUSERSITE=1` e `PYTHONPATH=""` sia in
build sia in `Verbatim.bat`. Verificato: import isolato di torch/pipeline + trascrizione reale
end-to-end girano dalla sola cartella portable.

**File PyInstaller** (`build/verbatim.spec`) lasciati nel repo come riferimento; `app/launcher.py`
è riusato dalla versione portable per avviare uvicorn e aprire il browser.

**Risk (pinned):** l'installer NON è firmato → Windows SmartScreen "Editore sconosciuto"; togliere
l'avviso richiede un certificato di code-signing a pagamento (non fornito) → l'insegnante clicca
"Esegui comunque". Il pacchetto include dipendenze di sviluppo (pytest, headers torch): opzionale
snellirle per ridurre la dimensione dell'installer.
