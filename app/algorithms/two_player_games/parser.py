from __future__ import annotations

import csv
from io import StringIO
from typing import List

from .schema import TPGInput


def read_csv(csv_text: str) -> List[List[str]]:
    if not isinstance(csv_text, str):
        raise ValueError(f"Ожидается строка, получено: {type(csv_text).__name__}")

    csv_text = csv_text.lstrip("\ufeff").strip()
    if not csv_text:
        raise ValueError("CSV пустой")

    sample = csv_text[:4096]

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    f = StringIO(csv_text)
    reader = csv.reader(f, delimiter=delimiter)

    rows = [
        [cell.strip().replace("#ДЕЛ/0!", "").replace("#DIV/0!", "") for cell in row]
        for row in reader
    ]

    if len(rows) < 5:
        raise ValueError("CSV слишком короткий")

    return rows


def _get_cell(rows: List[List[str]], row_idx: int, col_idx: int) -> str:
    if row_idx < 0 or row_idx >= len(rows):
        return ""
    row = rows[row_idx]
    if col_idx < 0 or col_idx >= len(row):
        return ""
    return row[col_idx].strip()


def _parse_float(value: str, field_name: str) -> float:
    raw = value.strip().replace(",", ".")
    if raw == "":
        raise ValueError(f"Поле '{field_name}' пустое")

    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Поле '{field_name}' должно быть числом, получено: '{value}'")


def _validate_template(rows: List[List[str]]) -> None:
    if _get_cell(rows, 0, 0) != "TPG":
        raise ValueError("Неверный шаблон: в ячейке A1 должна быть сигнатура 'TPG'")

    if _get_cell(rows, 13, 3) != "TPG":
        raise ValueError("Неверный шаблон: в ячейке D14 должна быть сигнатура 'TPG'")

    if _get_cell(rows, 17, 24) != "TPG":
        raise ValueError("Неверный шаблон: в ячейке Y18 должна быть сигнатура 'TPG'")


def _detect_matrix_size(rows: List[List[str]]) -> tuple[int, int]:
    """
    Матрица исходов находится в диапазоне:
    - строки: 4..13 (Excel)
    - пары столбцов: F:G, H:I, J:K, L:M, N:O, P:Q, R:S, T:U, V:W, X:Y

    В каждой паре:
    - первый столбец = выигрыш игрока 1
    - второй столбец = выигрыш игрока 2
    """
    matrix_start_row = 3
    max_rows = 10

    pair_start_cols = [5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    max_cols = len(pair_start_cols)

    detected_rows = 0
    met_empty_row = False

    for i in range(max_rows):
        row_idx = matrix_start_row + i
        has_any = False

        for col in pair_start_cols:
            if _get_cell(rows, row_idx, col) != "" or _get_cell(rows, row_idx, col + 1) != "":
                has_any = True
                break

        if has_any:
            if met_empty_row:
                raise ValueError(
                    "Платежная матрица заполнена с разрывами по строкам: "
                    "после пустой строки найдена непустая"
                )
            detected_rows += 1
        else:
            met_empty_row = True

    detected_cols = 0
    met_empty_col = False

    for col in pair_start_cols:
        has_any = False

        for i in range(max_rows):
            row_idx = matrix_start_row + i
            if _get_cell(rows, row_idx, col) != "" or _get_cell(rows, row_idx, col + 1) != "":
                has_any = True
                break

        if has_any:
            if met_empty_col:
                raise ValueError(
                    "Платежная матрица заполнена с разрывами по столбцам: "
                    "после пустого столбца найдена непустая пара столбцов"
                )
            detected_cols += 1
        else:
            met_empty_col = True

    if detected_rows == 0 or detected_cols == 0:
        raise ValueError("Платежная матрица не содержит данных")

    for i in range(detected_rows):
        row_idx = matrix_start_row + i
        for j in range(detected_cols):
            col = pair_start_cols[j]
            v1 = _get_cell(rows, row_idx, col)
            v2 = _get_cell(rows, row_idx, col + 1)

            if v1 == "" or v2 == "":
                raise ValueError(
                    f"Для исхода [{i + 1}, {j + 1}] должны быть заполнены оба выигрыша "
                    f"(игрока 1 и игрока 2)"
                )

    return detected_rows, detected_cols


def _parse_row_strategy_names(rows: List[List[str]], rows_count: int) -> list[str]:
    """
    Названия стратегий игрока 1 берём из E4:E13.
    """
    result: list[str] = []

    for i in range(rows_count):
        value = _get_cell(rows, 3 + i, 4)
        if value == "":
            raise ValueError(f"Не заполнено название стратегии игрока 1 №{i + 1}")
        result.append(value)

    return result


def _parse_col_strategy_names(rows: List[List[str]], cols_count: int) -> list[str]:
    """
    Названия стратегий игрока 2 берём из заголовков:
    F3, H3, J3, L3, N3, P3, R3, T3, V3, X3
    """
    pair_start_cols = [5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    result: list[str] = []

    for j in range(cols_count):
        value = _get_cell(rows, 2, pair_start_cols[j])
        if value == "":
            raise ValueError(f"Не заполнено название стратегии игрока 2 №{j + 1}")
        result.append(value)

    return result


def _parse_payoff_matrices(
    rows: List[List[str]],
    rows_count: int,
    cols_count: int,
) -> tuple[list[list[float]], list[list[float]]]:
    pair_start_cols = [5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    matrix_p1: list[list[float]] = []
    matrix_p2: list[list[float]] = []

    for i in range(rows_count):
        row_idx = 3 + i
        row_p1: list[float] = []
        row_p2: list[float] = []

        for j in range(cols_count):
            col = pair_start_cols[j]

            v1 = _parse_float(
                _get_cell(rows, row_idx, col),
                f"Выигрыш игрока 1 [{i + 1}, {j + 1}]",
            )
            v2 = _parse_float(
                _get_cell(rows, row_idx, col + 1),
                f"Выигрыш игрока 2 [{i + 1}, {j + 1}]",
            )

            row_p1.append(v1)
            row_p2.append(v2)

        matrix_p1.append(row_p1)
        matrix_p2.append(row_p2)

    return matrix_p1, matrix_p2


def validate_input(file_content: str) -> TPGInput:
    try:
        rows = read_csv(file_content)
    except Exception as e:
        raise ValueError(f"Ошибка чтения файла: {e}")

    _validate_template(rows)

    rows_count, cols_count = _detect_matrix_size(rows)

    row_strategy_names = _parse_row_strategy_names(rows, rows_count)
    col_strategy_names = _parse_col_strategy_names(rows, cols_count)

    payoff_matrix_p1, payoff_matrix_p2 = _parse_payoff_matrices(
        rows=rows,
        rows_count=rows_count,
        cols_count=cols_count,
    )

    return TPGInput(
        payoff_matrix_p1=payoff_matrix_p1,
        payoff_matrix_p2=payoff_matrix_p2,
        row_strategy_names=row_strategy_names,
        col_strategy_names=col_strategy_names,
    )
