"""CSV loading helpers."""

from __future__ import annotations

import csv
from pathlib import Path


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return [], []
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    return fieldnames, rows
