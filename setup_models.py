"""Scarica una sola volta tutti i modelli nella cache locale (poi: offline).

Eseguire dopo l'installazione delle dipendenze:
    python setup_models.py

La logica vera è in app/setup.py (condivisa con la UI di primo avvio dell'app impacchettata).
"""
from app.setup import download_all


def main():
    download_all(progress=lambda msg: print(msg, flush=True))
    print("\nFatto. Tutti i modelli sono in cache. Il programma ora funziona offline.")


if __name__ == "__main__":
    main()
