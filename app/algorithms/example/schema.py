import io, csv
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
        raise ValueError("CSV файл не содержит данных")
    row = rows[0]
    if "a" not in row or "b" not in row:
        raise ValueError("Отсутствуют обязательные колонки: a, b")
    try:
        a = float(row["a"])
        b = float(row["b"])
    except ValueError:
        raise ValueError("Значения колонок a и b должны быть числами")
    return ExampleInput(a=a, b=b)