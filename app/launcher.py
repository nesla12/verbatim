"""Avvio dell'app impacchettata: porta libera, server in background, browser, finestrella.

Usato dall'eseguibile PyInstaller (modalita' windowed, senza console). Avvia uvicorn in
un thread, apre il browser sulla pagina locale e mostra una piccola finestra di controllo;
chiudendola si termina il programma.
"""
from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(port: int, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.2):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _control_window(url: str) -> None:
    """Finestra minima: 'Verbatim è in esecuzione'. Chiuderla termina il programma."""
    try:
        import tkinter as tk
    except Exception:
        while True:  # nessun Tk: resta vivo finché il processo viene chiuso
            time.sleep(3600)
        return

    root = tk.Tk()
    root.title("Verbatim")
    root.geometry("360x150")
    root.resizable(False, False)
    tk.Label(root, text="Verbatim è in esecuzione", font=("Segoe UI", 13, "bold")).pack(pady=(22, 4))
    tk.Label(root, text="La trascrizione è aperta nel browser.", fg="#555").pack()
    tk.Button(root, text="Apri di nuovo nel browser",
              command=lambda: webbrowser.open(url)).pack(pady=8)
    tk.Label(root, text="Chiudi questa finestra per uscire.", fg="#999",
             font=("Segoe UI", 8)).pack(side="bottom", pady=8)
    root.mainloop()
    os._exit(0)  # ferma anche il thread del server


def main() -> None:
    import uvicorn

    # import diretto (NON la stringa "app.main:app"): così PyInstaller include nel pacchetto
    # tutta la catena app.main -> pipeline -> modelli.
    from app.main import app as fastapi_app

    # hook per test/diagnostica (innocui in produzione):
    #   VERBATIM_PORT     -> porta fissa invece di una libera
    #   VERBATIM_NO_WINDOW-> niente finestra Tk né browser: server in primo piano (per smoke test)
    port = int(os.environ.get("VERBATIM_PORT") or _free_port())
    no_window = os.environ.get("VERBATIM_NO_WINDOW") == "1"

    config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    if no_window:
        server.run()  # bloccante, utile per i test
        return

    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    if _wait_until_up(port):
        webbrowser.open(url)
    _control_window(url)


if __name__ == "__main__":
    main()
