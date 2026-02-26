from dataclasses import dataclass
from typing import List
import csv
from io import StringIO


@dataclass(frozen=True)
class AHPInput:
    n: int                          # количество критериев = количество альтернатив
    criteria_names: List[str]       # названия критериев, например ["Цена", "Качество", "Скорость"]
    pairwise: List[List[float]]     # матрица парных сравнений критериев (n × n)
    alt_names: List[str]            # названия альтернатив, например ["Ноутбук A", "Ноутбук B"]
    scores: List[List[float]]       # матрица оценок: [критерий][альтернатива]


def validate_input(data: dict) -> AHPInput:
    """
    Ожидаемый формат входа (пример):
    {
        "csv": "строка с содержимым csv-файла",
        # опционально можно добавить позже:
        # "n": 5,
        # "criteria": ["К1", "К2", ...],
        # но пока полагаемся только на csv
    }
    """
    if "csv" not in data:
        raise ValueError("Обязательное поле: csv (содержимое CSV-файла)")

    csv_text = str(data["csv"]).strip()
    if not csv_text:
        raise ValueError("CSV пустой")

    # Читаем CSV
    f = StringIO(csv_text)
    reader = csv.reader(f)
    rows = [row for row in reader if any(cell.strip() for cell in row)]

    if len(rows) < 4:
        raise ValueError("CSV слишком короткий для метода AHP")

    # ───────────────────────────────────────
    # 1. Определяем размер матрицы (n)
    # ───────────────────────────────────────
    # Предполагаем, что первая строка с числами/пустыми — это начало матрицы критериев
    first_data_row = None
    for row in rows:
        numeric_count = sum(1 for cell in row[1:] if cell.strip() and cell.replace(".", "").replace("-", "").isdigit())
        if numeric_count >= 2:  # хотя бы пара чисел → вероятно матрица
            first_data_row = row
            break

    if first_data_row is None:
        raise ValueError("Не удалось найти матрицу парных сравнений в CSV")

    n = len(first_data_row) - 1  # минус первый столбец (метки строк)
    if n < 2:
        raise ValueError("Матрица должна содержать минимум 2 критерия")
    if n > 19:
        raise ValueError("Максимально поддерживается 19 критериев / альтернатив")

    # ───────────────────────────────────────
    # 2. Читаем названия критериев и матрицу парных сравнений
    # ───────────────────────────────────────
    criteria_names = []
    pairwise = [[0.0] * n for _ in range(n)]

    crit_row_idx = 0
    for i, row in enumerate(rows):
        if len(row) < n + 1:
            continue
        # предполагаем, что строка начинается с названия критерия
        crit_name = row[0].strip()
        if not crit_name:
            crit_name = f"К{crit_row_idx + 1}"
        criteria_names.append(crit_name)

        for j in range(n):
            cell = row[j + 1].strip()
            if cell == '' or cell == '#DIV/0!':
                val = 0.0
            else:
                try:
                    val = float(cell)
                except ValueError:
                    raise ValueError(f"Невозможно преобразовать в число значение '{cell}' в строке {i+1}, столбец {j+2}")
            pairwise[crit_row_idx][j] = val

        crit_row_idx += 1
        if crit_row_idx == n:
            break

    if len(criteria_names) != n:
        raise ValueError(f"Ожидалось {n} критериев, найдено {len(criteria_names)}")

    # Заполняем диагональ и реципрокные значения
    for i in range(n):
        pairwise[i][i] = 1.0
        for j in range(i + 1, n):
            a = pairwise[i][j]
            b = pairwise[j][i]
            if a != 0 and b == 0:
                pairwise[j][i] = 1.0 / a
            elif b != 0 and a == 0:
                pairwise[i][j] = 1.0 / b
            # если оба ненулевые → оставляем как есть (можно потом проверять согласованность)

    # ───────────────────────────────────────
    # 3. Читаем матрицу оценок альтернатив
    # ───────────────────────────────────────
    alt_names = []
    scores = [[0.0] * n for _ in range(n)]  # [критерий][альтернатива]

    alt_start_found = False
    alt_row_idx = 0

    for row in rows:
        if not alt_start_found:
            # ищем начало блока альтернатив (по наличию слова "альт" или по количеству чисел)
            numeric_count = sum(1 for cell in row[1:] if cell.strip() and cell.replace(".", "").replace("-", "").isdigit())
            if numeric_count >= n - 2 or "альт" in str(row).lower() or "a" in str(row).lower():
                alt_start_found = True
            else:
                continue

        if len(row) < n + 1:
            continue

        alt_name = row[0].strip()
        if not alt_name:
            alt_name = f"А{alt_row_idx + 1}"
        alt_names.append(alt_name)

        for j in range(n):
            cell = row[j + 1].strip()
            if cell == '' or cell == '#DIV/0!':
                val = 0.0
            else:
                try:
                    val = float(cell)
                except ValueError:
                    raise ValueError(f"Невозможно преобразовать в число значение '{cell}' в оценках альтернативы {alt_name}")
            scores[j][alt_row_idx] = val  # важно: scores[критерий][альтернатива]

        alt_row_idx += 1
        if alt_row_idx == n:
            break

    if len(alt_names) != n:
        raise ValueError(f"Ожидалось {n} альтернатив, найдено {len(alt_names)}")

    return AHPInput(
        n=n,
        criteria_names=criteria_names,
        pairwise=pairwise,
        alt_names=alt_names,
        scores=scores,
    )

"""@dataclass(frozen=True)
class ExampleInput:
    a: float
    b: float

def validate_input(data: dict) -> ExampleInput:
    if "a" not in data or "b" not in data:
        raise ValueError("Input must contain fields: a, b")
    return ExampleInput(a=float(data["a"]), b=float(data["b"]))"""
