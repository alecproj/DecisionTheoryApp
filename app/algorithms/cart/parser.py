from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from .schema import CARTInput


def _read_csv(csv_text: str) -> list[list[str]]:
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

    reader = csv.reader(StringIO(csv_text), delimiter=delimiter)

    rows = [[cell.strip() for cell in row] for row in reader]
    rows = [row for row in rows if any(cell != "" for cell in row)]

    if len(rows) < 2:
        raise ValueError("Нужно минимум 2 строки: заголовок и данные")

    return rows


def _trim_trailing_empty(row: list[str]) -> list[str]:
    result = list(row)

    while result and result[-1] == "":
        result.pop()

    return result


def _normalize_row_length(row: list[str], expected_len: int, row_number: int) -> list[str]:
    result = list(row)

    if len(result) < expected_len:
        result += [""] * (expected_len - len(result))

    if len(result) > expected_len:
        extra = result[expected_len:]

        if any(cell != "" for cell in extra):
            raise ValueError(
                f"Строка {row_number}: ожидалось {expected_len} колонок, "
                f"получено {len(result)}"
            )

        result = result[:expected_len]

    return result


def _parse_feature_value(value: str, row_number: int, column_name: str) -> Any:
    value = value.strip()

    if value == "":
        raise ValueError(f"Строка {row_number}: пустое значение признака '{column_name}'")

    normalized = value.replace(",", ".")

    try:
        return float(normalized)
    except ValueError:
        return value


def validate_input(file_content: str) -> CARTInput:
    try:
        rows = _read_csv(file_content)
    except Exception as e:
        raise ValueError(f"Ошибка чтения файла: {e}")

    headers = _trim_trailing_empty([cell.strip() for cell in rows[0]])

    if len(headers) < 3:
        raise ValueError(
            "Нужно минимум 3 колонки: Режим, хотя бы один признак и целевая переменная"
        )

    if headers[0] != "Режим":
        raise ValueError("Первая колонка должна называться 'Режим'")

    if len(set(headers)) != len(headers):
        raise ValueError("Названия колонок не должны повторяться")

    target_name = headers[-1]

    if target_name == "Режим":
        raise ValueError("Последняя колонка должна быть целевой переменной, а не 'Режим'")

    feature_names = headers[1:-1]

    X_train: list[list[Any]] = []
    y_train: list[str] = []

    X_test: list[list[Any]] = []
    y_test: list[str] = []

    X_predict: list[list[Any]] = []

    allowed_sets = {"Тренировка", "Проверка", "Предсказание"}

    for raw_idx, raw_row in enumerate(rows[1:], start=2):
        row = _normalize_row_length(
            row=[cell.strip() for cell in raw_row],
            expected_len=len(headers),
            row_number=raw_idx,
        )

        set_name = row[0]

        if set_name not in allowed_sets:
            raise ValueError(
                f"Строка {raw_idx}: колонка Режим должна быть Тренировка, Проверка или Предсказание"
            )

        features = [
            _parse_feature_value(value, raw_idx, column_name)
            for value, column_name in zip(row[1:-1], feature_names)
        ]

        target = row[-1].strip()

        if set_name in {"Тренировка", "Проверка"} and target == "":
            raise ValueError(
                f"Строка {raw_idx}: для {set_name} нужна целевая переменная '{target_name}'"
            )

        if set_name == "Предсказание" and target != "":
            raise ValueError(
                f"Строка {raw_idx}: для 'Предсказание' целевая переменная должна быть пустой"
            )

        if set_name == "Тренировка":
            X_train.append(features)
            y_train.append(target)
        elif set_name == "Проверка":
            X_test.append(features)
            y_test.append(target)
        else:
            X_predict.append(features)

    if len(X_train) < 2:
        raise ValueError("В 'Тренировке' должно быть минимум 2 объекта")

    if len(set(y_train)) < 2:
        raise ValueError("В 'Тренировке' должно быть минимум 2 разных класса")

    if len(X_test) == 0:
        raise ValueError("Нужна хотя бы одна строка 'Проверка' для проверки качества")

    return CARTInput(
        feature_names=feature_names,
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        X_predict=X_predict,
        max_depth=4,
        min_samples_split=2,
    )
