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


def _start_server(port: int, no_window: bool) -> None:
    """Carica i modelli e avvia uvicorn. Aggiorna _state per la finestra di avvio."""
    try:
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
        if _wait_until_up(port):
            webbrowser.open(url)
        _state["url"] = url
        _state["ready"] = True
    except Exception as e:  # noqa: BLE001
        _state["error"] = str(e)


def _window() -> None:
    """Finestra di avvio: barra animata + stato; poi 'Verbatim è in esecuzione'."""
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        # nessun Tk disponibile: niente finestra, il processo resta vivo finché chiuso
        while True:
            time.sleep(3600)

    root = tk.Tk()
    root.title("Verbatim")
    root.geometry("400x190")
    root.resizable(False, False)

    title = tk.Label(root, text="Verbatim si sta avviando…", font=("Segoe UI", 13, "bold"))
    title.pack(pady=(24, 6))
    msg = tk.Label(root, text=_state["phase"], fg="#555", font=("Segoe UI", 10),
                   wraplength=360, justify="center")
    msg.pack()
    bar = ttk.Progressbar(root, mode="indeterminate", length=280)
    bar.pack(pady=14)
    bar.start(12)
    hint = tk.Label(root, text="Il browser si aprirà da solo. Non chiudere questa finestra.",
                    fg="#999", font=("Segoe UI", 8))
    hint.pack(side="bottom", pady=10)

    state_ui = {"btn": None}

    def tick() -> None:
        if _state["error"]:
            title.config(text="Si è verificato un errore")
            msg.config(text=_state["error"], fg="#b00020")
            bar.stop()
            bar.pack_forget()
            hint.config(text="Chiudi questa finestra e riprova. Se persiste, contatta l'assistenza.")
            return
        if _state["ready"]:
            title.config(text="Verbatim è in esecuzione")
            msg.config(text="La trascrizione è aperta nel browser.", fg="#555")
            bar.stop()
            bar.pack_forget()
            hint.config(text="Chiudi questa finestra per uscire.")
            if state_ui["btn"] is None:
                state_ui["btn"] = tk.Button(root, text="Apri di nuovo nel browser",
                                            command=lambda: webbrowser.open(_state["url"]))
                state_ui["btn"].pack(pady=6)
            return
        msg.config(text=_state["phase"])
        root.after(300, tick)

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
