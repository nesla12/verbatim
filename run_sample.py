"""Esecuzione da riga di comando: trascrive un file e scrive il JSON di progetto.

Uso:  python run_sample.py <percorso_audio>
Stampa il percorso del JSON prodotto e un riassunto dei primi segmenti.
"""
import sys
from pathlib import Path

from app.pipeline import transcribe as pipe


def main():
    if len(sys.argv) < 2:
        print("Uso: python run_sample.py <percorso_audio>")
        sys.exit(1)
    src = Path(sys.argv[1])
    if not src.exists():
        print(f"File non trovato: {src}")
        sys.exit(1)

    def cb(done, total):
        print(f"  segmento {done}/{total}", flush=True)

    print(f"Trascrizione di {src.name} ...")
    project = pipe.transcribe_file(src, original_name=src.name, progress=cb)
    out = pipe.project_path(project["id"])
    print(f"\nJSON di progetto: {out}")
    print(f"Durata: {project['duration']} s — {len(project['segments'])} segmenti\n")
    for seg in project["segments"][:5]:
        print(f"[{seg['start']:.2f}-{seg['end']:.2f}]")
        print(f"  LETTERALE: {seg['literal']}")
        print(f"  leggibile: {seg['readable']}")


if __name__ == "__main__":
    main()
