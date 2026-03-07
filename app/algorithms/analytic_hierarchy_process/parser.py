import csv
import math
from io import StringIO
from typing import List, Optional, Tuple

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
    В нашем случае сигнатура — 'AHP' в ячейках A1, A8 и A23.
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

def validate_scores(scores: List[List[float]], criterias_cnt: int):
    validate_matrix(scores, "scores", allow_zero=True, allow_negative=True)
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
            # --- Верхнетреугольная часть ---
            if a != 0:
                if a <= 0:
                    raise ValueError(f"Верхнетреугольный элемент pairwise [{i}][{j}] должен быть положительным: {a}")
                if a > 20:
                    raise ValueError(f"Верхнетреугольный элемент pairwise [{i}][{j}] превышает 20: {a}")
            # --- Нижнетреугольная часть ---
            if b != 0:
                if b <= 0:
                    raise ValueError(f"Нижнетреугольный элемент pairwise [{j}][{i}] должен быть положительным: {b}")
                if b > 20:
                    raise ValueError(f"Нижнетреугольный элемент pairwise [{j}][{i}] превышает 20: {b}")
            # --- Нормализация ---
            if a > 0 and b == 0:
                pairwise[j][i] = 1.0 / a

            elif b > 0 and a == 0:
                pairwise[i][j] = 1.0 / b

            elif a > 0 and b > 0:
                if abs(a * b - 1.0) > 0.02:
                    raise ValueError(f"Несоответствие в pairwise [{i}][{j}] и [{j}][{i}]: "f"{a} и {b} не обратны")

# ==========================================================
# ПАРСИНГ КРИТЕРИЕВ
# ==========================================================

def find_pairwise_matrix(rows: List[List[str]]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if not cell or _is_number(cell):
                continue

            # Считаем количество чисел справа
            numbers_right = 0
            for k in range(j+1, len(row)):
                if _is_number(row[k]):
                    numbers_right += 1
                else:
                    break
            if numbers_right >= 2 and i + 1 < len(rows) and len(rows[i+1]) > j and rows[i+1][j] and not _is_number(rows[i+1][j]):
                # нашли возможный старт
                pairwise_start = i
                name_col = j
                max_m = 0
                for offset in range(30):  # максимум 30 строк подряд
                    r_idx = i + offset
                    if r_idx >= len(rows) or len(rows[r_idx]) <= j or not rows[r_idx][j] or _is_number(rows[r_idx][j]):
                        break
                    num_count = 0
                    for c in range(j+1, len(rows[r_idx])):
                        if _is_number(rows[r_idx][c]):
                            num_count += 1
                        else:
                            break
                    if num_count > max_m:
                        max_m = num_count
                if max_m >= 2:
                    return pairwise_start, name_col, max_m
    return None, None, None


def parse_pairwise(rows: List[List[str]], pairwise_start: int, name_col: int, max_m: int):
    criteria_names = []
    pairwise = [[0.0] * max_m for _ in range(max_m)]
    row_idx = pairwise_start
    crit_count = 0

    while row_idx < len(rows) and crit_count < max_m:
        row = rows[row_idx]
        if len(row) <= name_col or not row[name_col] or _is_number(row[name_col]):
            break
        criteria_names.append(row[name_col].strip())
        for j in range(max_m):
            col = name_col + 1 + j
            if col >= len(row) or not row[col].strip():
                raise ValueError(f"Пустая ячейка в матрице pairwise, строка {row_idx + 1}, колонка {col + 1}")
            val = row[col]
            if _is_number(val):
                pairwise[crit_count][j] = _parse_number(val)
            else:
                raise ValueError(f"Некорректное значение в pairwise [{row_idx + 1}][{col + 1}]: '{val}'")
        crit_count += 1
        row_idx += 1
    return criteria_names, pairwise, crit_count

def parse_criteria_table(rows: List[List[str]]):
    pairwise_start, name_col, max_m = find_pairwise_matrix(rows)
    if pairwise_start is None:
        raise ValueError("Не найдена матрица критериев")
    criteria_names, pairwise, criterias_cnt = parse_pairwise(rows, pairwise_start, name_col, max_m)
    validate_matrix(pairwise, "criteria_pairwise", allow_zero=False, allow_negative=False)
    normalize_and_validate_pairwise(pairwise, criterias_cnt)
    return criteria_names, pairwise, criterias_cnt

# ==========================================================
# ПАРСИНГ АЛЬТЕРНАТИВ
# ==========================================================

def parse_alternative_names(rows: List[List[str]]) -> List[str]:
    for i, row in enumerate(rows):
        if any(cell.strip() == "Значения критериев" for cell in row):
            header_row = rows[i+1]
            names = [cell.strip() for cell in header_row if cell and not _is_number(cell) and "Сортировать" not in cell]
            if not names:
                raise ValueError("Не удалось спарсить названия альтернатив")
            return names
    raise ValueError("Не найден блок 'Значения критериев'")

def parse_scores(rows: List[List[str]], criteria_names: List[str], data_row_start: int, criterias_cnt: int, alternatives_cnt: int):
    scores = [[0.0] * alternatives_cnt for _ in range(criterias_cnt)]
    criteria_found = 0

    for i in range(data_row_start, len(rows)):
        if criteria_found >= criterias_cnt:
            break

        row = rows[i]
        crit_name_expected = criteria_names[criteria_found]

        if crit_name_expected in row:
            name_col = row.index(crit_name_expected)

            for alt_idx in range(alternatives_cnt):
                col = name_col + 1 + alt_idx
                if col >= len(row):
                    raise ValueError(f"Отсутствует значение для критерия '{crit_name_expected}', колонка {col+1}")

                val = row[col]
                if not val.strip():
                    raise ValueError(f"Пустая ячейка для критерия '{crit_name_expected}', колонка {col+1}")

                if _is_number(val):
                    scores[criteria_found][alt_idx] = _parse_number(val)
                else:
                    raise ValueError(f"Некорректное значение для критерия '{crit_name_expected}', колонка {col+1}: '{val}'")

            criteria_found += 1

    if criteria_found < criterias_cnt:
        raise ValueError(f"Не все критерии найдены в таблице альтернатив (найдено {criteria_found} из {criterias_cnt})")

    return scores

def parse_sort_asc(rows: List[List[str]], criteria_names: List[str], data_row_start: int, criterias_cnt: int, alternatives_cnt: int):
    sort_flags = [True] * criterias_cnt
    criteria_found = 0

    for i in range(data_row_start, len(rows)):
        if criteria_found >= criterias_cnt:
            break

        row = rows[i]
        crit_name_expected = criteria_names[criteria_found]

        if crit_name_expected in row:
            name_col = row.index(crit_name_expected)

            # где начинается поиск флага
            search_start = name_col + 1 + alternatives_cnt

            flag = None

            # ищем первую непустую ячейку справа
            for j in range(search_start, len(row)):
                cell = row[j].strip()
                if cell != "":
                    flag = cell
                    break

            if flag is None:
                raise ValueError(
                    f"Флага сортировки для критерия '{crit_name_expected}' нет"
                )

            if flag not in ('0', '1'):
                raise ValueError(
                    f"Флаг сортировки для критерия '{crit_name_expected}' не является 0 или 1: '{flag}'"
                )

            sort_flags[criteria_found] = flag == '1'
            criteria_found += 1

    if criteria_found < criterias_cnt:
        missing = criteria_names[criteria_found]
        raise ValueError(
            f"Не все критерии найдены в таблице сортировки "
            f"(найдено {criteria_found} из {criterias_cnt}, пропущен '{missing}')"
        )

    return sort_flags


def parse_alternative_table(rows: List[List[str]], criteria_names: List[str], criterias_cnt: int):
    alternative_names = parse_alternative_names(rows)
    alternatives_cnt = len(alternative_names)
    validate_sizes(criterias_cnt, alternatives_cnt)

    # ищем индекс первой альтернативы в строке заголовка
    for i, row in enumerate(rows):
        if any(cell.strip() == "Значения критериев" for cell in row):
            alt_header_row = i + 1
            header_row = rows[alt_header_row]
            break
    alt_start_col = None
    for j, cell in enumerate(header_row):
        if cell.strip() == alternative_names[0]:
            alt_start_col = j
            break
    if alt_start_col is None:
        raise ValueError("Не удалось определить столбец альтернатив")

    # парсим значения
    scores = parse_scores(rows, criteria_names, alt_header_row+1, criterias_cnt, alternatives_cnt)
    sort_flags = parse_sort_asc(rows, criteria_names, alt_header_row+1, criterias_cnt, alternatives_cnt)
    validate_scores(scores, criterias_cnt)

    return alternative_names, scores, sort_flags, alternatives_cnt

# ==========================================================
# ГЕНЕРАЦИЯ МАТРИЦ АЛЬТЕРНАТИВ
# ==========================================================

def calc_alternative_pairwise(scores, sort_flags):
    criterias_cnt = len(scores)
    alternatives_cnt = len(scores[0])
    result = []
    for i in range(criterias_cnt):
        matrix = [[1.0]*alternatives_cnt for _ in range(alternatives_cnt)]
        for a in range(alternatives_cnt):
            for b in range(alternatives_cnt):
                if a == b:
                    continue
                matrix[a][b] = scores[i][b]/scores[i][a] if sort_flags[i] else scores[i][a]/scores[i][b]
        result.append(matrix)
    return result