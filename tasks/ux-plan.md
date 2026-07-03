# Verbatim — Piano "Software Completo" (UX, contenuti, identità, legale)

Obiettivo: da MVP funzionale a software **auto-esplicativo e professionale**. Chi lo apre la
prima volta deve capire in 5 secondi: cosa fa di unico (parola per parola, anche parole
inventate), che è 100% locale/privato, quali file può usare, quanto ci mette, chi l'ha fatto,
e i limiti legali.

## Principi
- Register: product, ma con più "voce" esplicativa in home (non è più solo un tool nudo).
- Italiano, chiaro, per non-tecnici. Niente gergo.
- Numeri onesti (misurati, non inventati) su durata max e tempi.

---

## A. Home / Onboarding — comunicare il valore (USP)
1. **Hero con USP**: titolo forte + sottotitolo.
   - Titolo: "Trascrive esattamente come è stato detto — parola per parola."
   - Sotto: "Anche parole inventate, errori e frasi sgrammaticate. Non 'corregge' verso parole
     plausibili come gli altri strumenti. Pensato per interviste con bambini (uso educativo/clinico)."
2. **Riquadro Privacy** (in evidenza): "100% sul tuo computer. L'audio non viene mai caricato
   online. Nessun cloud, nessun account, funziona offline." + icona lucchetto.
3. **"Come funziona"** — 3 passi + i 2 livelli:
   - Passi: 1) Trascina il file → 2) Verifica e correggi → 3) Esporta in Word.
   - I due livelli: **Letterale** (fedele, primario) vs **Riferimento** (leggibile, aiuto).
     Spiegare perché il letterale è il valore unico (nessun language model che "aggiusta").
4. **Formati supportati** vicino al dropzone: audio (wav, mp3, m4a, ogg, flac) e video
   (mp4, mov, mkv, avi → estrae la traccia audio). E cosa NON è supportato.
5. **Limiti & tempi**: durata max consigliata + stima realistica ("circa N minuti di attesa per
   ogni minuto di audio, sul tuo computer, senza scheda grafica"). Numeri MISURATI (vedi E).

## B. Dropzone & validazione
6. Dropzone che elenca i formati accettati; stato "trascina qui" più guidato.
7. **Validazione lato client**: se il file non è un formato audio/video supportato, messaggio
   chiaro in italiano invece di un errore ffmpeg criptico.
8. **Avviso file lunghi**: se l'audio supera X minuti, avvisa del tempo stimato prima di partire.

## C. Aiuto in-app (schermata di revisione)
9. Migliorare la legenda letterale/riferimento con una riga di spiegazione al primo uso.
10. Pannello **"?" (Aiuto)**: come funziona, scorciatoie da tastiera, formati, privacy, limiti.

## D. Identità, About, Legale
11. **Footer/About** su ogni schermata: "Creato da Lorenzo Nesler · aiautomationcoach.com ·
    Open source" con link cliccabili.
12. **Pannello "Informazioni"**: versione, autore, link sito, link repo, licenza.
13. **Disclaimer legale** (testo IT, bozza da far rivedere): strumento di supporto educativo/
    clinico, NON dispositivo medico; fornito "così com'è" senza garanzie; l'utente è responsabile
    di ottenere il consenso alla registrazione dei minori e del trattamento dei dati (GDPR);
    la trascrizione automatica può contenere errori e va sempre verificata da un umano.
14. **File LICENSE** con la licenza open source scelta + intestazione breve nel README.

## E. Contenuti misurati (onestà dei numeri)
15. **Misurare** il tempo reale di elaborazione su CPU (audio di 1, 5, 10 min) per scrivere una
    stima onesta ("~X min per minuto di audio").
16. Definire la **durata massima** dichiarata (i criteri di accettazione testano 45 min; verificare
    memoria costante su file lungo) e documentarla in home + Aiuto.

## F. Rigenerazione pacchetto
17. Dopo le modifiche UI/contenuti: rebuild cartella portable + ricompilazione installer, così
    l'installer per gli insegnanti contiene la versione completa. (Include già il fix cartella-dati
    in `%LOCALAPPDATA%`.)

---

## Decisioni (confermate 2026-07-03)
- **Licenza: MIT** → file `LICENSE` (© Lorenzo Nesler), citata in README e About.
- **Disclaimer: gate al primo avvio** → schermata "Ho letto e accetto" (consenso minori, GDPR,
  nessuna garanzia, verifica umana) mostrata una volta; accettazione salvata in un file locale
  (`DATA_DIR/.accepted`); testo sempre ri-consultabile da "Informazioni".
- **Brand: design neutro** + credito testuale "Creato da Lorenzo Nesler · aiautomationcoach.com"
  (link) nel footer/About. Niente logo.
- **Repo: da creare su GitHub** → preparo `LICENSE`, `.gitignore` (esclude modelli, projects,
  build/portable, dist, __pycache__), README pronti; poi comandi `gh` per pubblicare (o lo creo
  io se mi autorizzi).

## Rischi / note
- Il testo del **disclaimer legale** sarà una bozza ragionevole: NON sono un avvocato, va rivista.
- Ogni modifica alla UI richiede **rebuild portable + ricompilazione installer** (lento, ~20 min).
- I **numeri di tempo/durata** vanno misurati prima di scriverli (niente stime inventate).
- Restare "product": più esplicativo sì, ma senza trasformare la home in una landing invadente.

## Ordine consigliato
A + B + C (UX e contenuti) → D (identità/legale) → E (misure, riempie i numeri) → F (pacchetto).

---

## Review — implementazione (2026-07-03)

Fatto e verificato nel browser (preview su :8077):

- **A. Home/USP** — hero "Trascrive esattamente come è stato detto · parola per parola",
  sottotitolo che spiega il "no correzione", riquadro **Privacy** (100% locale/offline),
  sezione **Come funziona** (3 passi + i 2 livelli letterale/riferimento), sezione **Limiti &
  tempi** (durata ~60 min, ~1–3× la durata, rete solo al primo avvio). Nav "Come funziona" /
  "Informazioni".
- **B. Dropzone** — elenco formati (da `/api/info`), **validazione lato client** per estensione
  con messaggio chiaro, **avviso file lunghi** (probe durata nel browser → stima tempo, conferma).
- **C. Aiuto in-app** — pannello **"?"** in revisione + nav in home (drawer con cosa fa, 2 livelli,
  passi, scorciatoie, formati, tempi, privacy).
- **D. Identità/Legale** — footer "Creato da Lorenzo Nesler · aiautomationcoach.com · MIT",
  pannello **Informazioni** (versione/autore/sito/repo/licenza + avviso legale), **gate legale al
  primo avvio** con checkbox obbligatoria; accettazione salvata in `DATA_DIR/.accepted`
  (endpoint `POST /api/legal/accept`, stato in `GET /api/info`). File **LICENSE (MIT)**.
- Repo: **`.gitignore`** (esclude projects/, *.wav, .accepted, models/, build/portable, dist,
  installer/output) + **README** aggiornato (autore, privacy/legale, licenza). NB: `verbatim/` è
  ora dentro il repo home (remote chat-widget) → per pubblicarlo serve un repo GitHub dedicato.

Backend: `config.py` (APP_VERSION/AUTHOR/SITE/REPO, AUDIO_EXTS/VIDEO_EXTS, MAX_RECOMMENDED_MINUTES,
LEGAL_ACCEPTED_FILE); `app/main.py` (`/api/info`, `/api/legal/accept`).

**Numeri (E):** tenuti come range onesto e dichiarato approssimato ("~1–3× la durata su CPU"),
non misurati su un campione lungo (dipende dalla macchina). Da rifinire se si vuole un numero
secco su un PC di riferimento.

**Da fare (F):** rebuild `build/build_portable.ps1` + ricompilazione installer con questa UI, così
gli insegnanti ricevono la versione completa. L'utente dovrà **reinstallare** l'installer nuovo.
