"""Confronta le chiavi del catalogo statico Juice Shop con la matrice locale."""
import argparse
import csv
import re
from pathlib import Path

MATRIX = Path(__file__).resolve().parents[1] / "sfide.csv"


def compare(source, matrix=MATRIX):
    # Nel formato upstream ogni record ha una chiave top-level su una riga.
    keys = re.findall(r"^  key: ([A-Za-z][A-Za-z0-9_]*)[ \t]*\r?$",
                      source.read_text(encoding="utf-8"), re.MULTILINE)
    with matrix.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    mapped = [row["key"] for row in rows]
    if not keys or len(keys) != len(set(keys)) or len(mapped) != len(set(mapped)):
        raise ValueError("Catalogo vuoto, formato inatteso o chiavi duplicate")
    return sorted(set(keys) - set(mapped)), sorted(set(mapped) - set(keys))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalogo", type=Path)
    args = parser.parse_args()
    nuove, assenti = compare(args.catalogo)
    print("Da mappare:", ", ".join(nuove) or "nessuna")
    print("Assenti nel catalogo esaminato:", ", ".join(assenti) or "nessuna")
    raise SystemExit(int(bool(nuove or assenti)))
