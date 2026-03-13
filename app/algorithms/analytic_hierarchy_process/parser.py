import csv
import math
from io import StringIO
from typing import List, Tuple, Optional

# ==========================================================
# БАЗОВЫЕ УТИЛИТЫ
# ==========================================================

def _is_number(s: str) -> bool:
    if not s or not s.strip():
        return False
    s = s.strip().replace(',', '.')
    try:
        float(s)
        return True
    except ValueError:
        return False

def _parse_number(s: str) -> float:
    s = s.strip().replace(',', '.')
    if not s:
        raise ValueError("Пустая строка не может быть числом")
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Некорректное число: '{s}'")

def read_csv(csv_text: str) -> List[List[str]]:
    if not isinstance(csv_text, str):
        raise ValueError(f"Ожидается строка, получено: {type(csv_text).__name__}")
    f = StringIO(csv_text.strip())
    reader = csv.reader(f, delimiter=';')
    rows = [
        [cell.strip().replace('#ДЕЛ/0!', '').replace('#DIV/0!', '') for cell in r]
        for r in reader
    ]
    if len(rows) < 5:
        raise ValueError("CSV слишком короткий")
    return rows

# ==========================================================
# ВАЛИДАЦИЯ
# ==========================================================

def validate_template(rows: List[List[str]]) -> None:
    """
    Проверяет наличие сигнатуры шаблона.
    Сигнатура — 'AHP' в ячейках A1, A8 и A23.
    """
    sig_cells = [
        (0, 0),   # A1
        (7, 0),   # A8
        (22, 0),  # A23
    ]
    for r, c in sig_cells:
        if r >= len(rows):
            raise ValueError(f"Неверный шаблон CSV — строка {r+1} отсутствует")
        if c >= len(rows[r]):
            raise ValueError(f"Неверный шаблон CSV — колонка {c+1} отсутствует в строке {r+1}")
        if rows[r][c].strip() != "AHP":
            raise ValueError(f"Неверный шаблон CSV — сигнатура не найдена в ячейке {r+1},{c+1}")

def validate_sizes(criterias_cnt: int, alternatives_cnt: int) -> None:
    if criterias_cnt > 19 or alternatives_cnt > 19:
        raise ValueError("Количество критериев или альтернатив превышает 19")
    if criterias_cnt == 0 or alternatives_cnt == 0:
        raise ValueError("Не найдены критерии или альтернативы")

def validate_matrix(matrix: List[List[float]], name: str, allow_zero: bool = True, allow_negative: bool = False) -> None:
    for i, row in enumerate(matrix):
        for j, val in enumerate(row):
            if not isinstance(val, float):
                raise ValueError(f"Элемент в матрице {name} [{i}][{j}] не является числом: {val}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Элемент в матрице {name} [{i}][{j}] является NaN или inf: {val}")
            if not allow_negative and val < 0:
                raise ValueError(f"Отрицательное значение в матрице {name} [{i}][{j}]: {val}")
            if not allow_zero and val == 0:
                raise ValueError(f"Нулевое значение в матрице {name} [{i}][{j}], где не ожидалось: {val}")

def validate_scores(scores: List[List[float]], criterias_cnt: int) -> None:
    validate_matrix(scores, "scores", allow_zero=False, allow_negative=False)
    for i in range(criterias_cnt):
        if all(v == 0 for v in scores[i]):
            raise ValueError(f"Строка {i} в scores полностью нулевая")

def normalize_and_validate_pairwise(pairwise: List[List[float]], m: int) -> None:
    for i in range(m):
        if pairwise[i][i] != 1.0:
            raise ValueError(f"Диагональный элемент в pairwise [{i}][{i}] не равен 1.0: {pairwise[i][i]}")
        for j in range(i + 1, m):
            a = pairwise[i][j]
            b = pairwise[j][i]
            if a != 0:
                if a <= 0:
                    raise ValueError(f"Верхнетреугольный элемент pairwise [{i}][{j}] должен быть положительным: {a}")
                if a > 20:
                    raise ValueError(f"Верхнетреугольный элемент pairwise [{i}][{j}] превышает 20: {a}")
            if b != 0:
                if b <= 0:
                    raise ValueError(f"Нижнетреугольный элемент pairwise [{j}][{i}] должен быть положительным: {b}")
                if b > 20:
                    raise ValueError(f"Нижнетреугольный элемент pairwise [{j}][{i}] превышает 20: {b}")
            if a > 0 and b == 0:
                pairwise[j][i] = 1.0 / a
            elif b > 0 and a == 0:
                pairwise[i][j] = 1.0 / b
            elif a > 0 and b > 0:
                if abs(a * b - 1.0) > 0.02:
                    raise ValueError(
                        f"Несоответствие в pairwise [{i}][{j}] и [{j}][{i}]: "
                        f"{a} и {b} не обратны"
                    )

# ==========================================================
# ПАРСИНГ НАЗВАНИЙ
# ==========================================================

def parse_alternative_names(rows: List[List[str]]) -> List[str]:
    """
    Читает названия альтернатив из диапазона C10:C28
    (rows[9:28], col 2).
    """
    names = []
    for row in rows[9:28]:
        if len(row) <= 2:
            continue
        cell = row[2].strip()
        if cell:
            names.append(cell)
    if not names:
        raise ValueError("Не найдены названия альтернатив в диапазоне C10:C28")
    return names


def parse_criteria_names(rows: List[List[str]]) -> List[str]:
    """
    Читает названия критериев из диапазона F10:F28
    (rows[9:28], col 5).
    """
    names = []
    for row in rows[9:28]:
        if len(row) <= 5:
            continue
        cell = row[5].strip()
        if cell:
            names.append(cell)
    if not names:
        raise ValueError("Не найдены названия критериев в диапазоне F10:F28")
    return names

# ==========================================================
# ПАРСИНГ МАТРИЦЫ КРИТЕРИЕВ
# ==========================================================

def parse_criteria_table(rows: List[List[str]]) -> Tuple[List[str], List[List[float]], int]:
    """
    Читает матрицу попарных сравнений критериев из диапазона I3:AA21
    (rows[2:21], cols[8:27]).
    Размер матрицы определяется количеством критериев из F10:F28.
    """
    criteria_names = parse_criteria_names(rows)
    detected = count_filled_cells(rows[2], start_col=8, max_count=19)  # строка I3
    if detected == 0:
        raise ValueError("Не найдены данные в матрице критериев I3:AA21")
    if detected > len(criteria_names):
        raise ValueError(
            f"В матрице критериев {detected} столбцов, "
            f"но названий критериев только {len(criteria_names)}"
        )
    # работаем только с тем, что заполнено
    criterias_cnt = detected
    criteria_names = criteria_names[:criterias_cnt]
    pairwise = [[0.0] * criterias_cnt for _ in range(criterias_cnt)]

    for i in range(criterias_cnt):
        row_idx = 2 + i  # I3 → row index 2
        if row_idx >= len(rows):
            raise ValueError(f"Строка {row_idx + 1} отсутствует в диапазоне матрицы критериев I3:AA21")
        row = rows[row_idx]
        for j in range(criterias_cnt):
            col_idx = 8 + j  # col I → index 8
            if col_idx >= len(row):
                raise ValueError(f"Ячейка [{i+1}][{j+1}] отсутствует в матрице критериев")
            cell = row[col_idx].strip()
            if not cell:
                raise ValueError(f"Пустая ячейка в матрице критериев [{i+1}][{j+1}]")
            if not _is_number(cell):
                raise ValueError(f"Некорректное значение в матрице критериев [{i+1}][{j+1}]: '{cell}'")
            pairwise[i][j] = _parse_number(cell)

    validate_matrix(pairwise, "criteria_pairwise", allow_zero=False, allow_negative=False)
    normalize_and_validate_pairwise(pairwise, criterias_cnt)

    return criteria_names, pairwise, criterias_cnt

# ==========================================================
# ПАРСИНГ ТАБЛИЦЫ ЗНАЧЕНИЙ КРИТЕРИЕВ
# ==========================================================

def parse_alternative_table(
    rows: List[List[str]],
    criteria_names: List[str],
    criterias_cnt: int,
) -> Tuple[List[str], List[List[float]], List[bool], int]:
    """
    Читает:
    - названия альтернатив из C10:C28  (rows[9:28],  col 2)
    - значения критериев  из I25:AA43  (rows[24:43], cols[8:27])
    - флаги сортировки    из AB25:AB43 (rows[24:43], col 27)
    """
    alternative_names = parse_alternative_names(rows)

    detected = count_filled_cells(rows[24], start_col=8, max_count=19)  # строка I25
    if detected == 0:
        raise ValueError("Не найдены значения альтернатив в диапазоне I25:AA25")
    if detected > len(alternative_names):
        raise ValueError(
            f"В таблице значений {detected} столбцов, "
            f"но названий альтернатив только {len(alternative_names)}"
        )
    alternatives_cnt = detected
    alternative_names = alternative_names[:alternatives_cnt]

    validate_sizes(criterias_cnt, alternatives_cnt)

    scores:     List[List[float]] = [[0.0] * alternatives_cnt for _ in range(criterias_cnt)]
    sort_flags: List[bool]        = []

    for i in range(criterias_cnt):
        row_idx = 24 + i  # I25 → row index 24
        if row_idx >= len(rows):
            raise ValueError(f"Строка {row_idx + 1} отсутствует в диапазоне значений I25:AA43")
        row = rows[row_idx]

        # --- значения критериев (cols I...) ---
        for j in range(alternatives_cnt):
            col_idx = 8 + j  # col I → index 8
            if col_idx >= len(row):
                raise ValueError(f"Значение для критерия {i+1}, альтернативы {j+1} отсутствует")
            cell = row[col_idx].strip()
            if not cell:
                raise ValueError(f"Пустая ячейка значений критерия {i+1}, альтернативы {j+1}")
            if not _is_number(cell):
                raise ValueError(f"Некорректное значение критерия {i+1}, альтернативы {j+1}: '{cell}'")
            scores[i][j] = _parse_number(cell)

        # --- флаг сортировки (col AB → index 27) ---
        col_sort = 27
        if col_sort >= len(row):
            raise ValueError(f"Флаг сортировки для критерия {i+1} отсутствует (колонка AB)")
        flag = row[col_sort].strip()
        if flag not in ('0', '1'):
            raise ValueError(f"Флаг сортировки для критерия {i+1} должен быть 0 или 1, получено: '{flag}'")
        sort_flags.append(flag == '1')

    validate_scores(scores, criterias_cnt)

    return alternative_names, scores, sort_flags, alternatives_cnt

# ==========================================================
# ГЕНЕРАЦИЯ МАТРИЦ АЛЬТЕРНАТИВ
# ==========================================================

def calc_alternative_pairwise(
    scores: List[List[float]],
    sort_flags: List[bool],
) -> List[List[List[float]]]:
    criterias_cnt    = len(scores)
    alternatives_cnt = len(scores[0])
    result = []

    for i in range(criterias_cnt):
        matrix = [[1.0] * alternatives_cnt for _ in range(alternatives_cnt)]
        for a in range(alternatives_cnt):
            for b in range(alternatives_cnt):
                if a == b:
                    continue
                divisor = scores[i][a] if sort_flags[i] else scores[i][b]
                if divisor == 0:
                    raise ValueError(
                        f"Деление на ноль при построении матрицы альтернатив: "
                        f"критерий {i}, альтернатива {a if sort_flags[i] else b}"
                    )
                matrix[a][b] = (
                    scores[i][b] / scores[i][a]
                    if sort_flags[i]
                    else scores[i][a] / scores[i][b]
                )
        result.append(matrix)
    return result

def count_filled_cells(row: List[str], start_col: int, max_count: int) -> int:
    count = 0
    for k in range(max_count):
        col_idx = start_col + k
        if col_idx >= len(row):
            break
        if not row[col_idx].strip():
            break
        count += 1
    return count