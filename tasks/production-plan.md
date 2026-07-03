# Verbatim — Production Plan (features for teachers)

Phase after MVP. Goal: a real, installable, day-to-day tool for non-technical teachers /
educators, fully offline, single user per machine.

## Decisions (confirmed with user 2026-06-11)
- **Deployment:** per-teacher local laptop, fully offline, single user. No accounts, no server.
- **Packaging:** one-click `.exe` installer (PyInstaller). No Python/terminal for the teacher.
- **Speakers:** automatic diarization (proposes) + manual labels (teacher corrects).
- **Feature scope this phase:** Project library + management. (Folder/batch import, .srt export,
  settings panel = DEFERRED to a later phase.)

## What MUST stay the same (non-negotiable)
- Literal layer: wav2vec2 CTC greedy, **no LM**, no post-correction. Untouched.
- **Zero network at transcription time.** Diarization models also download once at setup, then offline.
- Italian UI, literal text primary / readable muted. The current redesign stays; we extend it.
- Existing JSON projects keep working (schema migration, not breakage).
- Existing acceptance tests keep passing.

---

## Work items

### 1. Data model + migration
1.1. Bump `SCHEMA_VERSION` to 2. On `load_project`, migrate v1→v2 in memory: add
     `segment["speaker"] = ""` where missing; add `project["speakers"] = []` (known labels).
1.2. `transcribe_file` writes `speaker: ""` per segment and `speakers: []` by default.

### 2. Project library + management (backend)
2.1. `GET /api/projects` — extend: include `created` (file mtime), sort newest first.
2.2. `PATCH /api/project/{id}` — rename (`{"name": "..."}`), validates non-empty.
2.3. `DELETE /api/project/{id}` — remove project JSON + its audio WAV. (Teacher-triggered only.)
2.4. Startup reconcile: on app start, any project JSON stuck in `status:"processing"` whose
     job is not in `_progress` → set `status:"interrupted"` so the library shows truth after a
     restart/crash. Progress endpoint falls back to the JSON status when not in memory.

### 3. Project library + management (frontend, home screen)
3.1. On load, `GET /api/projects` and render a **library list** below the dropzone: each row =
     name (serif), duration, segment count, status badge, date.
3.2. Row actions: open, rename (inline), delete (confirm dialog in Italian — destructive).
3.3. Simple client-side search box (filter by name).
3.4. Upload jobs merge into the same list (a processing row becomes a library row when done),
     so progress is visible and survives navigation. Keep current per-file progress bar.

### 4. Speaker diarization (automatic) + manual labels
4.1. `app/pipeline/diarize.py` — **offline, non-gated**: per VAD-segment speaker embedding via
     SpeechBrain ECAPA-TDNN (`speechbrain/spkrec-ecapa-voxceleb`, non-gated, runs on the torch
     CPU we already have) + agglomerative clustering. Default 2 speakers (child + interviewer),
     with an `n_speakers` arg (auto/clustering threshold fallback). Reuses existing segments;
     never touches the literal text.
4.2. `setup_models.py` — pre-download the ECAPA model (single-threaded, same symlink-safe path).
4.3. `POST /api/project/{id}/diarize` — background thread, progress like transcription; assigns
     `segment["speaker"]` = "Interlocutore 1/2…"; teacher renames afterward.
4.4. Frontend review screen:
     - "Identifica interlocutori" button (with progress) in the toolbar.
     - Per-segment speaker chip in the time gutter; click to pick/rename from the project's
       speaker set or type a custom name (e.g. "Bambino", "Maestra"). Color-coded per speaker.
     - Renaming a speaker updates all its segments (PATCH project speakers + segment speaker).
4.5. Exports use `segment["speaker"]` in the (previously empty) speaker column. `.docx` and
     `.txt` updated. Default export still literal-text-primary.

### 5. One-click installer (PyInstaller)
5.1. `build/verbatim.spec` — bundle FastAPI app + static + Python runtime + torch/onnxruntime
     into a windowed launcher exe. Hidden imports for uvicorn/transformers/onnx-asr/speechbrain.
5.2. Launcher (`app/launcher.py`): pick a free localhost port, start uvicorn in-process, open the
     default browser, keep a tray/console-less process; clean shutdown.
5.3. **Models are NOT bundled** (too large). First run shows an Italian **setup screen** in the UI:
     - `GET /api/setup/status` reports which models are cached.
     - `POST /api/setup/download` runs `setup_models` in the background with progress.
     - The UI blocks transcription until models are present, with a clear "una tantum" message.
     - Model cache pinned to `%LOCALAPPDATA%\Verbatim\models` via `HF_HOME` so it persists/offline.
5.4. `installer/` — Inno Setup script (or a self-extracting zip + Start-menu/desktop shortcut)
     that places the exe and a data dir. Document the build steps in `BUILD.md`.

### 6. Tests + docs
6.1. `test_diarize.py` — two concatenated distinct-speaker fixtures cluster into 2 labels;
     diarization never alters `literal` text; runs offline.
6.2. `test_library_api.py` — rename, delete (on a temp project), startup reconcile of a stuck
     "processing" project, projects listing/sorting.
6.3. `test_schema_migration.py` — a v1 JSON loads as v2 with speaker fields defaulted.
6.4. Update `test_offline.py` to also cover the diarization path with network blocked.
6.5. Update README (teacher quickstart: install → first-run model download → use) + `BUILD.md`
     (developer packaging steps). Update `DECISIONS.md` (D6 diarization choice, D7 packaging).

---

## Risks / blockers (read before approving)
- **R1 — PyInstaller + torch/onnxruntime on Windows is the high-risk item.** Large artifact
  (~1 GB libs even without models), hidden-import and DLL pitfalls, and iterative debugging
  likely. Mitigation: models download on first run (not bundled); budget time for build trial.
- **R2 — Unsigned exe → Windows SmartScreen/AV warnings.** No code-signing certificate available;
  teachers will see a "publisher unknown" prompt. Real code signing needs a paid cert (out of
  scope unless you provide one).
- **R3 — Diarization must stay non-gated + offline.** pyannote's pretrained pipeline is
  license-gated (needs HF token/terms) → rejected. Using SpeechBrain ECAPA (non-gated) + our own
  clustering. Adds the `speechbrain` dependency tree.
- **R4 — Diarization accuracy on child speech is imperfect.** It proposes; the teacher corrects.
  UI and copy set this expectation; not a "magic" auto-label.
- **R5 — First run needs internet once** on the teacher's machine to fetch models, then fully
  offline. Consistent with the spec ("download once at setup").
- **R6 — Data deletion** is built as a teacher-triggered action with confirmation; the assistant
  will not auto-delete anyone's project data.

## Open question
- **Q1:** For the installer, do you have (or want me to assume none) a code-signing certificate?
  Without one, R2's "unknown publisher" warning is unavoidable. If you have a cert, I'll wire
  signing into the build; if not, I'll document the SmartScreen "Run anyway" step for teachers.

## Suggested build order
1 → 2 → 3 (library usable) → 4 (speakers) → 6 tests alongside → 5 packaging last (riskiest,
benefits from a stable feature set). Each step keeps the app runnable and tests green.
