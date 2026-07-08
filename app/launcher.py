"""Avvio dell'app: finestra "sto caricando" IMMEDIATA, server in background, poi browser.

Appena si lancia (Verbatim.bat), compare subito una finestrella con una barra animata e un
messaggio di stato ("Preparazione dei modelli…", "Avvio del motore…", "Apertura del browser…"),
così l'utente vede che il programma sta lavorando anche durante i ~20-40 s del primo avvio.
Quando il server è pronto, il browser si apre da solo e la finestra diventa il pannello di
controllo ("Verbatim è in esecuzione"). Chiuderla termina il programma.

Hook per test/diagnostica (innocui in produzione):
  VERBATIM_PORT      -> porta fissa invece di una libera
  VERBATIM_NO_WINDOW -> niente finestra né browser: server in primo piano (per smoke test)
"""
from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser

# stato condiviso tra il thread di avvio e la finestra
_state = {"phase": "Preparazione dei modelli…", "url": None, "ready": False, "error": None}


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.2):
                return True
        except OSError:
            time.sleep(0.15)
    return False


# tempo minimo in cui la finestra di caricamento resta visibile, così l'utente la nota
# sempre (anche quando i modelli sono già in cache e l'avvio è quasi istantaneo).
_MIN_SPLASH_S = 3.0


def _start_server(port: int, no_window: bool) -> None:
    """Carica i modelli e avvia uvicorn. Aggiorna _state per la finestra di avvio."""
    try:
        t0 = time.time()
        _state["phase"] = "Preparazione dei modelli… (fino a un minuto al primo avvio)"
        import uvicorn

        # import diretto (NON la stringa "app.main:app"): tira dentro tutta la catena
        # app.main -> pipeline -> modelli. È QUI che si spende il tempo del primo avvio.
        from app.main import app as fastapi_app

        _state["phase"] = "Avvio del motore…"
        config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=port, log_level="warning")
        server = uvicorn.Server(config)

        if no_window:
            server.run()  # bloccante, utile per i test
            return

        threading.Thread(target=server.run, daemon=True).start()
        url = f"http://127.0.0.1:{port}"
        _state["phase"] = "Apertura del browser…"
        up = _wait_until_up(port)
        # tieni visibile la finestra di caricamento almeno qualche secondo
        rest = _MIN_SPLASH_S - (time.time() - t0)
        if rest > 0:
            time.sleep(rest)
        _state["url"] = url
        _state["ready"] = True          # la finestra mostra "Verbatim è pronto!"
        time.sleep(1.1)                  # lascia leggere il messaggio verde…
        if up:
            webbrowser.open(url)         # …poi apre il browser
    except Exception as e:  # noqa: BLE001
        _state["error"] = str(e)


def _window() -> None:
    """Finestra di avvio evidente: barra animata, cronometro, durata stimata e rassicurazione;
    poi diventa 'Verbatim è pronto'."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        # nessun Tk disponibile: niente finestra, il processo resta vivo finché chiuso
        while True:
            time.sleep(3600)

    # palette coerente con l'app (carta + indaco)
    PAPER, INK, MUTED, ACCENT, OK = "#faf8f4", "#2b2740", "#6b6880", "#4b3f8f", "#2e7d52"

    root = tk.Tk()
    root.title("Verbatim")
    root.configure(bg=PAPER)
    root.resizable(False, False)
    W, H = 500, 340
    x = (root.winfo_screenwidth() - W) // 2
    y = (root.winfo_screenheight() - H) // 3
    root.geometry(f"{W}x{H}+{x}+{y}")
    root.attributes("-topmost", True)                      # porta in primo piano all'avvio
    root.after(1800, lambda: root.attributes("-topmost", False))

    def lbl(text, font, fg, pady=(0, 0)):
        w = tk.Label(root, text=text, font=font, fg=fg, bg=PAPER,
                     wraplength=W - 56, justify="center")
        w.pack(pady=pady)
        return w

    lbl("Verbatim", ("Georgia", 20, "bold"), INK, (26, 2))
    title = lbl("Si sta avviando…", ("Segoe UI", 14, "bold"), INK, (0, 2))
    phase = lbl(_state["phase"], ("Segoe UI", 10), MUTED, (2, 4))

    # barra animata (spessa, ben visibile)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
        style.configure("V.Horizontal.TProgressbar", troughcolor="#ece8e0",
                        background=ACCENT, thickness=14, borderwidth=0)
        bar = ttk.Progressbar(root, mode="indeterminate", length=340,
                              style="V.Horizontal.TProgressbar")
    except Exception:
        bar = ttk.Progressbar(root, mode="indeterminate", length=340)
    bar.pack(pady=(6, 8))
    bar.start(11)

    timer = lbl("Tempo trascorso: 0 secondi", ("Segoe UI", 10, "bold"), ACCENT, (0, 10))

    info = lbl("Il primo avvio richiede di solito meno di un minuto: sta caricando i modelli "
               "linguistici. Le volte successive è molto più veloce.",
               ("Segoe UI", 9), MUTED, (0, 4))
    reassure = lbl("Puoi fare altro nel frattempo. Il browser si aprirà da solo quando è pronto — "
                   "lascia aperta questa finestra.", ("Segoe UI", 9), MUTED, (0, 0))

    state_ui = {"btn": None, "start": time.time()}

    def tick() -> None:
        if _state["error"]:
            title.config(text="Si è verificato un errore")
            phase.config(text=_state["error"], fg="#b00020")
            bar.stop(); bar.pack_forget(); timer.pack_forget()
            info.config(text="Chiudi questa finestra e riprova.")
            reassure.config(text="Se il problema continua, contatta l'assistenza.")
            return
        if _state["ready"]:
            title.config(text="Verbatim è pronto!", fg=OK)
            phase.config(text="La trascrizione è aperta nel tuo browser.", fg=MUTED)
            bar.stop(); bar.pack_forget(); timer.pack_forget()
            info.config(text="Se hai chiuso la scheda per sbaglio, riaprila col pulsante qui sotto.")
            reassure.config(text="Per uscire dal programma, chiudi questa finestra.")
            if state_ui["btn"] is None:
                state_ui["btn"] = tk.Button(root, text="Apri di nuovo nel browser",
                                            font=("Segoe UI", 10), bg=ACCENT, fg="white",
                                            activebackground="#3c3273", activeforeground="white",
                                            relief="flat", padx=14, pady=6, cursor="hand2",
                                            command=lambda: webbrowser.open(_state["url"]))
                state_ui["btn"].pack(pady=6)
            return
        phase.config(text=_state["phase"])
        elapsed = int(time.time() - state_ui["start"])
        timer.config(text=f"Tempo trascorso: {elapsed} second{'o' if elapsed == 1 else 'i'}")
        root.after(250, tick)

    tick()
    root.mainloop()
    os._exit(0)  # ferma anche il thread del server


def main() -> None:
    port = int(os.environ.get("VERBATIM_PORT") or _free_port())
    no_window = os.environ.get("VERBATIM_NO_WINDOW") == "1"

    if no_window:
        _start_server(port, True)
        return

    # il caricamento pesante gira in un thread; la finestra compare SUBITO
    threading.Thread(target=_start_server, args=(port, False), daemon=True).start()
    _window()


if __name__ == "__main__":
    main()
