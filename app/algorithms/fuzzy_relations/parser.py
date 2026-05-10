from __future__ import annotations

import csv
import math
from io import StringIO
from typing import List

from .schema import FuzzyRelationsInput


SIGNATURE = "FREL"

MAX_Y = 19
MAX_X = 19
MAX_Z = 19

# Сигнатуры шаблона.
# Координаты указаны в 0-based индексах, комментарии — в Excel-нотации.
SIGNATURE_CELLS = [
    (0, 0, "A1"),
    (7, 0, "A8"),
    (23, 0, "A24"),
]

# Списки названий элементов.
# Пользовательское название берем из name_col, а если оно пустое — код из code_col.
Y_NAMES_START_ROW = 9    # C10, fallback B10
Y_NAME_COL = 2
Y_CODE_COL = 1

X_NAMES_START_ROW = 9    # F10, fallback E10
X_NAME_COL = 5
X_CODE_COL = 4

Z_NAMES_START_ROW = 31   # C32, fallback B32
Z_NAME_COL = 2
Z_CODE_COL = 1

# Матрицы отношений.
R1_START_ROW = 2         # I3
R1_START_COL = 8

R2_START_ROW = 24        # I25
R2_START_COL = 8


# ==========================================================
# БАЗОВЫЕ УТИЛИТЫ
# ==========================================================

def read_csv(csv_text: str) -> List[List[str]]:
    """
    Читает CSV-текст, который backend получает после загрузки .csv
    или после преобразования первого листа .xlsx в CSV.

    Функция:
    - проверяет, что вход является строкой;
    - убирает BOM в начале файла;
    - автоматически определяет разделитель ',' или ';';
    - возвращает таблицу строк без пробелов по краям ячеек.
    """
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
    rows = [[cell.strip() for cell in row] for row in reader]

    if len(rows) < 5:
        raise ValueError("CSV слишком короткий")

    return rows


def _get_cell(rows: List[List[str]], row_idx: int, col_idx: int) -> str:
    """
    Безопасно возвращает значение ячейки по 0-based координатам.

    Если строка или столбец выходят за пределы таблицы, возвращается
    пустая строка. Это позволяет одинаково обрабатывать короткие CSV,
    пустые хвосты строк и отсутствующие столбцы.
    """
    if row_idx < 0 or row_idx >= len(rows):
        return ""

    row = rows[row_idx]
    if col_idx < 0 or col_idx >= len(row):
        return ""

    return row[col_idx].strip()


def _is_blank(value: str) -> bool:
    """
    Проверяет, что значение ячейки пустое после удаления пробелов.
    """
    return value.strip() == ""


def _is_excel_error(value: str) -> bool:
    """
    Определяет типовые ошибки Excel, которые не должны попадать
    в матрицы нечетких отношений.

    Это нужно, чтобы пользователь случайно не загрузил шаблон,
    оставшийся от метода анализа иерархий с формулами вида #DIV/0!.
    """
    value = value.strip().upper()
    return value.startswith("#") or value in {
        "#DIV/0!",
        "#ДЕЛ/0!",
        "#VALUE!",
        "#ЗНАЧ!",
        "#REF!",
        "#ССЫЛКА!",
        "#NAME?",
        "#ИМЯ?",
        "#N/A",
        "#Н/Д",
        "#NUM!",
        "#ЧИСЛО!",
    }


def _parse_float(value: str, field_name: str) -> float:
    """
    Преобразует строковое значение ячейки в float.
    Поддерживается десятичная точка и десятичная запятая. При ошибке
    формируется сообщение с названием поля, чтобы пользователь видел,
    какую именно ячейку нужно исправить.
    """
    raw = value.strip()

    if raw == "":
        raise ValueError(f"Поле '{field_name}' пустое")

    if _is_excel_error(raw):
        raise ValueError(
            f"Поле '{field_name}' содержит ошибку Excel: '{value}'. "
            "Проверьте, что в матрицах нет формул от другого шаблона"
        )

    raw = raw.replace(",", ".")

    try:
        number = float(raw)
    except ValueError:
        raise ValueError(f"Поле '{field_name}' должно быть числом, получено: '{value}'")

    if not math.isfinite(number):
        raise ValueError(f"Поле '{field_name}' должно быть конечным числом, получено: '{value}'")

    return number


def _parse_membership_value(value: str, field_name: str) -> float:
    """
    Читает значение степени принадлежности для матрицы отношения.

    Допустимый диапазон — [0; 1], потому что элементы R1 и R2 являются
    значениями функций принадлежности нечетких отношений.
    """
    number = _parse_float(value, field_name)

    if not (0.0 <= number <= 1.0):
        raise ValueError(
            f"Поле '{field_name}' должно находиться в диапазоне [0; 1], "
            f"получено: {value}"
        )

    return number


# ==========================================================
# ВАЛИДАЦИЯ ШАБЛОНА
# ==========================================================

def _validate_template(rows: List[List[str]]) -> None:
    """
    Проверяет служебные сигнатуры шаблона.

    Сигнатуры нужны, чтобы не принять за шаблон композиции нечетких
    отношений файл от другого алгоритма или произвольную таблицу.
    """
    for row_idx, col_idx, excel_addr in SIGNATURE_CELLS:
        value = _get_cell(rows, row_idx, col_idx)
        if value != SIGNATURE:
            raise ValueError(
                f"В ячейке {excel_addr} должна быть сигнатура "
                f"'{SIGNATURE}', получено: '{value}'"
            )


# ==========================================================
# ОПРЕДЕЛЕНИЕ РАЗМЕРОВ МАТРИЦ
# ==========================================================

def _detect_matrix_size(
    rows: List[List[str]],
    start_row: int,
    start_col: int,
    max_rows: int,
    max_cols: int,
    matrix_name: str,
) -> tuple[int, int]:
    """
    Определяет размер активного прямоугольника матрицы.

    - считаются подряд заполненные строки сверху;
    - считаются подряд заполненные столбцы слева;
    - после первой пустой строки/колонки нельзя снова вводить данные;
    - внутри найденного активного прямоугольника не допускаются пустые ячейки.

    Возвращает пару (число строк, число столбцов).
    """
    detected_rows = 0
    met_empty_row = False

    # Определяем количество активных строк матрицы.
    for i in range(max_rows):
        row_idx = start_row + i
        row_values = [_get_cell(rows, row_idx, start_col + j) for j in range(max_cols)]
        has_any = any(not _is_blank(value) for value in row_values)

        if has_any:
            if met_empty_row:
                raise ValueError(
                    f"Матрица {matrix_name} заполнена с разрывами по строкам: "
                    "после пустой строки найдена непустая"
                )
            detected_rows += 1
        else:
            met_empty_row = True

    detected_cols = 0
    met_empty_col = False

    # Определяем количество активных столбцов матрицы.
    for j in range(max_cols):
        col_idx = start_col + j
        col_values = [_get_cell(rows, start_row + i, col_idx) for i in range(max_rows)]
        has_any = any(not _is_blank(value) for value in col_values)

        if has_any:
            if met_empty_col:
                raise ValueError(
                    f"Матрица {matrix_name} заполнена с разрывами по столбцам: "
                    "после пустого столбца найден непустой"
                )
            detected_cols += 1
        else:
            met_empty_col = True

    if detected_rows == 0 or detected_cols == 0:
        raise ValueError(f"Матрица {matrix_name} не содержит данных")

    # Проверяем, что внутри активного прямоугольника нет пустых ячеек.
    for i in range(detected_rows):
        for j in range(detected_cols):
            value = _get_cell(rows, start_row + i, start_col + j)
            if _is_blank(value):
                raise ValueError(
                    f"Матрица {matrix_name} содержит пустую ячейку "
                    f"внутри заполненного диапазона [{i + 1}, {j + 1}]"
                )

    return detected_rows, detected_cols


def _validate_dimensions(
    r1_rows: int,
    r1_cols: int,
    r2_rows: int,
    r2_cols: int,
) -> None:
    """
    Проверяет совместимость размерностей R1 и R2.

    Для композиции оба отношения должны иметь одинаковое число строк Y:
    R1 имеет размер Y x X, R2 имеет размер Y x Z. Результат будет иметь
    размер X x Z.
    """
    if r1_rows != r2_rows:
        raise ValueError(
            "Матрицы R1 и R2 должны иметь одинаковое число строк Y: "
            f"в R1 найдено {r1_rows}, в R2 найдено {r2_rows}"
        )

    if not (1 <= r1_rows <= MAX_Y):
        raise ValueError(f"Количество элементов Y должно быть от 1 до {MAX_Y}")

    if not (1 <= r1_cols <= MAX_X):
        raise ValueError(f"Количество элементов X должно быть от 1 до {MAX_X}")

    if not (1 <= r2_cols <= MAX_Z):
        raise ValueError(f"Количество элементов Z должно быть от 1 до {MAX_Z}")


# ==========================================================
# ПАРСИНГ НАЗВАНИЙ
# ==========================================================

def _parse_name(
    rows: List[List[str]],
    row_idx: int,
    name_col: int,
    code_col: int,
    label: str,
    index: int,
) -> str:
    """
    Читает название одного элемента множества.

    Если пользовательское название пустое, используется технический код
    элемента из соседнего столбца: Y1, X1 или Z1. Это позволяет работать
    даже с минимально заполненным шаблоном.
    """
    name = _get_cell(rows, row_idx, name_col)
    code = _get_cell(rows, row_idx, code_col)

    result = name if name else code
    if result == "":
        raise ValueError(f"Не заполнено название элемента {label}{index}")

    return result


def _validate_unique_names(names: list[str], label: str) -> None:
    """
    Проверяет, что внутри одного множества нет повторяющихся названий.

    Сравнение выполняется без учета регистра и пробелов по краям.
    """
    seen: set[str] = set()

    for name in names:
        key = name.strip().lower()
        if key in seen:
            raise ValueError(f"В списке {label} найдено повторяющееся название: '{name}'")
        seen.add(key)


def _parse_names(
    rows: List[List[str]],
    start_row: int,
    name_col: int,
    code_col: int,
    count: int,
    label: str,
) -> list[str]:
    """
    Читает список названий элементов множества фиксированной длины.

    Длина списка берется не из блока названий, а из активного размера
    соответствующей матрицы. Это защищает от случайных незаполненных
    хвостов шаблона.
    """
    names = [
        _parse_name(
            rows=rows,
            row_idx=start_row + i,
            name_col=name_col,
            code_col=code_col,
            label=label,
            index=i + 1,
        )
        for i in range(count)
    ]

    _validate_unique_names(names, label)
    return names


# ==========================================================
# ПАРСИНГ МАТРИЦ
# ==========================================================

def _parse_relation_matrix(
    rows: List[List[str]],
    start_row: int,
    start_col: int,
    rows_count: int,
    cols_count: int,
    matrix_name: str,
) -> list[list[float]]:
    """
    Читает активную часть матрицы нечеткого отношения.

    Каждая ячейка преобразуется в float и проверяется как степень
    принадлежности в диапазоне [0; 1].
    """
    matrix: list[list[float]] = []

    for i in range(rows_count):
        row_values: list[float] = []

        for j in range(cols_count):
            value = _get_cell(rows, start_row + i, start_col + j)
            number = _parse_membership_value(
                value,
                f"{matrix_name}[{i + 1}, {j + 1}]",
            )
            row_values.append(number)

        matrix.append(row_values)

    return matrix


# ==========================================================
# ВНУТРЕННЯЯ ТОЧКА ПАРСИНГА
# ==========================================================

def parse_fuzzy_relations_input(file_content: str) -> FuzzyRelationsInput:
    """
    Выполняет полный цикл парсинга шаблона композиции нечетких отношений.

    Последовательность работы:
    1. прочитать CSV-текст;
    2. проверить сигнатуры шаблона;
    3. определить активные размеры R1 и R2;
    4. проверить совместимость размерностей;
    5. прочитать названия Y, X, Z;
    6. прочитать значения матриц R1 и R2;
    7. вернуть FuzzyRelationsInput.

    Публичной точкой входа для registry.py остается validate_input(...)
    из schema.py. Эта функция считается внутренней для parser.py.
    """
    try:
        rows = read_csv(file_content)
    except Exception as e:
        raise ValueError(f"Ошибка чтения файла: {e}")

    try:
        _validate_template(rows)
    except Exception as e:
        raise ValueError(f"Неверный шаблон: {e}")

    try:
        r1_rows, r1_cols = _detect_matrix_size(
            rows=rows,
            start_row=R1_START_ROW,
            start_col=R1_START_COL,
            max_rows=MAX_Y,
            max_cols=MAX_X,
            matrix_name="R1(Y, X)",
        )
        r2_rows, r2_cols = _detect_matrix_size(
            rows=rows,
            start_row=R2_START_ROW,
            start_col=R2_START_COL,
            max_rows=MAX_Y,
            max_cols=MAX_Z,
            matrix_name="R2(Y, Z)",
        )
        _validate_dimensions(r1_rows, r1_cols, r2_rows, r2_cols)
    except Exception as e:
        raise ValueError(f"Ошибка валидации размерности матриц: {e}")

    try:
        y_names = _parse_names(
            rows=rows,
            start_row=Y_NAMES_START_ROW,
            name_col=Y_NAME_COL,
            code_col=Y_CODE_COL,
            count=r1_rows,
            label="Y",
        )
        x_names = _parse_names(
            rows=rows,
            start_row=X_NAMES_START_ROW,
            name_col=X_NAME_COL,
            code_col=X_CODE_COL,
            count=r1_cols,
            label="X",
        )
        z_names = _parse_names(
            rows=rows,
            start_row=Z_NAMES_START_ROW,
            name_col=Z_NAME_COL,
            code_col=Z_CODE_COL,
            count=r2_cols,
            label="Z",
        )
    except Exception as e:
        raise ValueError(f"Ошибка чтения названий элементов множеств: {e}")

    try:
        r1 = _parse_relation_matrix(
            rows=rows,
            start_row=R1_START_ROW,
            start_col=R1_START_COL,
            rows_count=r1_rows,
            cols_count=r1_cols,
            matrix_name="R1",
        )
        r2 = _parse_relation_matrix(
            rows=rows,
            start_row=R2_START_ROW,
            start_col=R2_START_COL,
            rows_count=r2_rows,
            cols_count=r2_cols,
            matrix_name="R2",
        )
    except Exception as e:
        raise ValueError(f"Ошибка чтения значений нечетких отношений: {e}")

    return FuzzyRelationsInput(
        y_names=y_names,
        x_names=x_names,
        z_names=z_names,
        r1=r1,
        r2=r2,
    )
