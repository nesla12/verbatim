# Verbatim

Strumento **locale** per trascrivere interviste con bambini **esattamente come sono state
dette** — comprese parole inventate, errori di pronuncia, forme sgrammaticate e false partenze.
L'audio dei minori **non lascia mai il computer**.

Creato da **Lorenzo Nesler** · [aiautomationcoach.com](https://aiautomationcoach.com) · open source (licenza **MIT**).

---

## 📥 Come installare (per insegnanti — nessuna conoscenza tecnica)

> Non serve installare Python né altro. Bastano 3 passi.

**1. Scarica il programma**
Vai alla pagina **[Download / Releases »](https://github.com/nesla12/verbatim/releases/latest)**
e clicca su **`Verbatim-Setup.exe`**. È un file grande (~300 MB): il download può richiedere
qualche minuto.

**2. Aprilo con un doppio clic**
Windows potrebbe mostrare un avviso blu **"Windows ha protetto il PC / Editore sconosciuto"**.
È normale: significa solo che il programma non è firmato con un certificato a pagamento, **non**
che sia pericoloso (il codice è pubblico e aperto). Per continuare:
clicca su **"Ulteriori informazioni"** → poi sul pulsante **"Esegui comunque"**.

**3. Segui l'installazione e apri Verbatim**
Clicca *Avanti* fino alla fine. Alla fine trovi l'icona **Verbatim** sul desktop e nel menu Start:
doppio clic e si apre da solo nel browser.

**Al primo avvio** il programma scarica una sola volta i modelli (serve Internet, pochi minuti).
**Da lì in poi funziona anche senza Internet.** L'audio resta sempre e solo sul tuo computer.

Richiede **Windows 10 o 11**. Se qualcosa non è chiaro, dentro il programma c'è il pulsante
**"Come funziona"** che spiega tutto passo passo.

---

## Come funziona

Due livelli per ogni segmento di parlato:

- **LETTERALE** (primario, modificabile): modello acustico puro `wav2vec2-large-xlsr-53-italian`
  con decodifica CTC greedy **senza alcun language model**. Scrive lettera per lettera cio' che
  sente, senza "correggere" verso parole plausibili.
- **Leggibile** (riferimento secondario, sola lettura): `parakeet-tdt-0.6b-v3` (via onnx-asr),
  solo come aiuto di lettura. Non e' l'artefatto principale.
- **Interlocutori**: la diarizzazione automatica (offline) propone chi parla in ogni segmento;
  tu correggi e rinomini le etichette (es. "Bambino", "Maestra"). Finiscono negli export.

---

# Per sviluppatori

> Da qui in poi è materiale tecnico (avvio da codice, test, build). Gli insegnanti possono
> ignorarlo: basta l'installer descritto sopra.

## Requisiti

- Windows con **Python 3.11+**
- **ffmpeg** installato e nel PATH

## Installazione (una sola volta)

Doppio clic su **`install.bat`** (installa le dipendenze e scarica i modelli).
In alternativa, a mano:

```
pip install -r requirements.txt
pip install resemblyzer --no-deps
python setup_models.py
```

I modelli si scaricano una volta sola (serve Internet). Dopo, tutto funziona **offline**.

## Avvio

Doppio clic su **`start.bat`**. Si apre il browser sulla pagina di Verbatim.

## Uso

1. **Le tue trascrizioni**: la pagina iniziale elenca i lavori passati (apri, rinomina,
   elimina, cerca per nome). Lo stato di ogni file resta corretto anche dopo un riavvio.
2. Trascina uno o piu' file (audio o video). Vedi l'avanzamento per ciascuno.
3. Apri un file completato: lista dei segmenti con lettore audio.
   - Clic su un **segmento** o una **parola** per ascoltarne il tratto.
   - **Spazio** = play/pausa, **R** = ripeti il segmento.
4. Correggi il testo **letterale** (riga in alto). Le modifiche si salvano da sole.
5. **Identifica interlocutori**: assegna automaticamente chi parla; poi clicca l'etichetta di
   un segmento per correggerla, o un'etichetta nella legenda per rinominarla ovunque.
6. Esporta in **.txt** o **.docx** (con la colonna "Interlocutore" compilata dalle etichette).

## Versione installabile (per insegnanti, senza Python)

È possibile creare un eseguibile `.exe` che gli insegnanti avviano con un doppio clic, senza
Python e senza terminale. Vedi **`BUILD.md`**. Al primo avvio l'app scarica i modelli una volta
(serve Internet), poi funziona completamente offline.

## Riga di comando (opzionale)

```
python run_sample.py percorso\al\file.mp3
```

## Test

```
pytest -q
```

Include il test di **fedelta' sulle parole inventate** (le parole inventate devono restare
fonetiche), la **garanzia offline**, la coerenza dei **timestamp** e l'assenza di language model.

Vedi `DECISIONS.md` per le scelte architetturali e `tasks/todo.md` per il piano.

## Privacy e responsabilità legale

- **Tutto è locale.** L'audio e le trascrizioni restano sul computer; nessun caricamento online,
  nessun account. Dopo il primo avvio (download modelli) l'app funziona anche senza Internet.
- **Non è un dispositivo medico.** È uno strumento di supporto educativo/clinico. La trascrizione
  automatica **può contenere errori** e va sempre verificata da una persona.
- **Consenso e GDPR.** Registrare e trascrivere la voce di un minore richiede un consenso valido
  di chi ne ha la responsabilità genitoriale. Il responsabile del trattamento dei dati sei tu.
- Al primo avvio l'app mostra questo avviso e chiede di accettarlo una volta.

## Licenza

[MIT](LICENSE) © 2026 Lorenzo Nesler. Fornito "così com'è", senza garanzie.
