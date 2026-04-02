from __future__ import annotations

import csv
from io import StringIO
from typing import List

from .schema import Mode, DUUInput


def _read_csv(csv_text: str) -> List[List[str]]:
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
    if _get_cell(rows, 0, 0) != "DUU":
        raise ValueError("Неверный шаблон: в ячейке A1 должна быть сигнатура 'DUU'")

    if _get_cell(rows, 6, 5) != "DUU":
        raise ValueError("Неверный шаблон: в ячейке F7 должна быть сигнатура 'DUU'")

    if _get_cell(rows, 27, 25) != "DUU":
        raise ValueError("Неверный шаблон: в ячейке Z28 должна быть сигнатура 'DUU'")

    if _get_cell(rows, 2, 4) != "Значение":
        raise ValueError("Неверный шаблон: ожидается заголовок 'Значение' в ячейке E3")

    if _get_cell(rows, 2, 5) != "Параметр":
        raise ValueError("Неверный шаблон: ожидается заголовок 'Параметр' в ячейке F3")

    if _get_cell(rows, 9, 2) != "Название стратегии":
        raise ValueError("Неверный шаблон: ожидается заголовок 'Название стратегии' в ячейке C10")

    if _get_cell(rows, 9, 5) != "Название условия":
        raise ValueError("Неверный шаблон: ожидается заголовок 'Название условия' в ячейке F10")


def _parse_alpha(rows: List[List[str]]) -> float:
    alpha = _parse_float(_get_cell(rows, 3, 4), "Коэффициент оптимизма")
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("Коэффициент оптимизма должен находиться в диапазоне [0; 1]")
    return alpha


def _parse_mode(rows: List[List[str]]) -> Mode:
    mode = _get_cell(rows, 4, 4).lower()
    if mode not in ("max", "min"):
        raise ValueError("Поле 'Максимизация или минимизация' должно быть 'max' или 'min'")
    return mode  # type: ignore[return-value]


def _detect_matrix_size(rows: List[List[str]]) -> tuple[int, int]:
    """
    Определяет размер заполненного прямоугольника платежной матрицы I4:Z21.

    Логика:
    - число стратегий = число подряд заполненных строк сверху
    - число состояний = число подряд заполненных столбцов слева
    - внутри прямоугольника не допускаются пустые ячейки
    - после первой пустой строки/колонки заполнение дальше не допускается
    """
    matrix_start_row = 3  # Excel row 4
    matrix_end_row = 20  # Excel row 21
    matrix_start_col = 8  # Excel col I
    matrix_end_col = 25  # Excel col Z

    max_rows = matrix_end_row - matrix_start_row + 1
    max_cols = matrix_end_col - matrix_start_col + 1

    detected_rows = 0
    met_empty_row = False

    for i in range(max_rows):
        row_idx = matrix_start_row + i
        row_values = [_get_cell(rows, row_idx, matrix_start_col + j) for j in range(max_cols)]
        has_any = any(v != "" for v in row_values)

        if has_any:
            if met_empty_row:
                raise ValueError(
                    "Платёжная матрица заполнена с разрывами по строкам: "
                    "после пустой строки найдена непустая"
                )
            detected_rows += 1
        else:
            met_empty_row = True

    detected_cols = 0
    met_empty_col = False

    for j in range(max_cols):
        col_idx = matrix_start_col + j
        col_values = [_get_cell(rows, matrix_start_row + i, col_idx) for i in range(max_rows)]
        has_any = any(v != "" for v in col_values)

        if has_any:
            if met_empty_col:
                raise ValueError(
                    "Платёжная матрица заполнена с разрывами по столбцам: "
                    "после пустого столбца найден непустой"
                )
            detected_cols += 1
        else:
            met_empty_col = True

    if detected_rows == 0 or detected_cols == 0:
        raise ValueError("Платёжная матрица не содержит данных")

    for i in range(detected_rows):
        for j in range(detected_cols):
            value = _get_cell(rows, matrix_start_row + i, matrix_start_col + j)
            if value == "":
                raise ValueError(
                    f"Платёжная матрица содержит пустую ячейку "
                    f"внутри заполненного диапазона [{i + 1}, {j + 1}]"
                )

    return detected_rows, detected_cols


def _validate_counts(strategies_count: int, states_count: int) -> None:
    if strategies_count > 18:
        raise ValueError("Количество стратегий не должно превышать 18")

    if states_count > 18:
        raise ValueError("Количество состояний природы не должно превышать 18")


def _parse_strategy_names(rows: List[List[str]], strategies_count: int) -> list[str]:
    """
    Названия стратегий: C11:C28
    Берём ровно столько, сколько строк найдено в матрице.
    """
    result: list[str] = []

    for i in range(strategies_count):
        value = _get_cell(rows, 10 + i, 2)
        if value == "":
            raise ValueError(f"Не заполнено название стратегии {i + 1}")
        result.append(value)

    return result


def _parse_state_names(rows: List[List[str]], states_count: int) -> list[str]:
    """
    Названия условий: F11:F28
    Берём ровно столько, сколько столбцов найдено в матрице.
    """
    result: list[str] = []

    for j in range(states_count):
        value = _get_cell(rows, 10 + j, 5)
        if value == "":
            raise ValueError(f"Не заполнено название состояния природы {j + 1}")
        result.append(value)

    return result


def _validate_matrix_labels(
    rows: List[List[str]],
    strategies_count: int,
    states_count: int,
) -> None:
    for i in range(strategies_count):
        expected = f"С{i + 1}"
        actual = _get_cell(rows, 3 + i, 7)  # H
        if actual != expected:
            raise ValueError(
                f"Неверный шаблон платёжной матрицы: ожидалось '{expected}' "
                f"в строке {i + 4}, столбце H"
            )

    for j in range(states_count):
        expected = f"У{j + 1}"
        actual = _get_cell(rows, 2, 8 + j)  # I3:Z3
        if actual != expected:
            raise ValueError(
                f"Неверный шаблон платёжной матрицы: ожидалось '{expected}' "
                f"в строке 3, столбце {8 + j + 1}"
            )


def _parse_payoff_matrix(
    rows: List[List[str]],
    strategies_count: int,
    states_count: int,
) -> list[list[float]]:
    matrix: list[list[float]] = []

    matrix_start_row = 3  # row 4 in Excel
    matrix_start_col = 8  # col I in Excel

    for i in range(strategies_count):
        row_values: list[float] = []

        for j in range(states_count):
            cell_value = _get_cell(rows, matrix_start_row + i, matrix_start_col + j)
            number = _parse_float(
                cell_value,
                f"Платёжная матрица [{i + 1}, {j + 1}]",
            )
            row_values.append(number)

        matrix.append(row_values)

    return matrix


def validate_input(file_content: str) -> DUUInput:
    try:
        rows = _read_csv(file_content)
    except Exception as e:
        raise ValueError(f"Ошибка чтения файла: {e}")

    try:
        _validate_template(rows)
    except Exception as e:
        raise ValueError(f"Неверный шаблон: {e}")

    try:
        alpha = _parse_alpha(rows)
        mode = _parse_mode(rows)
    except Exception as e:
        raise ValueError(f"Ошибка чтения параметров: {e}")

    try:
        strategies_count, states_count = _detect_matrix_size(rows)
        _validate_counts(strategies_count, states_count)
        _validate_matrix_labels(rows, strategies_count, states_count)
    except Exception as e:
        raise ValueError(f"Ошибка валидации матрицы: {e}")


    try:
        strategy_names = _parse_strategy_names(rows, strategies_count)
        state_names = _parse_state_names(rows, states_count)
    except Exception as e:
        raise ValueError(f"Ошибка чтения имен: {e}")

    try:
        payoff_matrix = _parse_payoff_matrix(
            rows=rows,
            strategies_count=strategies_count,
            states_count=states_count,
        )
    except Exception as e:
        raise ValueError(f"Ошибка чтения матрицы: {e}")

    return DUUInput(
        payoff_matrix=payoff_matrix,
        mode=mode,
        alpha=alpha,
        strategy_names=strategy_names,
        state_names=state_names,
    )
