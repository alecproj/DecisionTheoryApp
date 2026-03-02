#schema.py
import io
import csv
from dataclasses import dataclass


@dataclass(frozen=True)
class ExampleInput:
    a: float
    b: float


def validate_input(file_bytes: bytes) -> ExampleInput:
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise ValueError("CSV файл пустой")

    row = rows[0]

    if "a" not in row or "b" not in row:
        raise ValueError("CSV должен содержать колонки: a, b")

    return ExampleInput(a=float(row["a"]), b=float(row["b"]))