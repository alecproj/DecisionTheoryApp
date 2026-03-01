# parser.py
import csv
from io import StringIO
from typing import Dict, Any, List, Optional


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
    if not s.strip():
        raise ValueError(f"Пустая строка не может быть числом: '{s}'")
    s_parsed = s.replace(',', '.')
    try:
        return float(s_parsed)
    except ValueError:
        raise ValueError(f"Некорректное число (содержит символы или неверный формат): '{s}'")


def find_pairwise_matrix(rows: List[List[str]]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    pairwise_start = name_col = max_m = None
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if not cell or _is_number(cell):
                continue
            numbers_right = 0
            for k in range(j + 1, len(row)):
                if _is_number(row[k]):
                    numbers_right += 1
                else:
                    break
            if numbers_right >= 3 and i + 1 < len(rows) and len(rows[i + 1]) > j and rows[i + 1][j] and not _is_number(rows[i + 1][j]):
                pairwise_start = i
                name_col = j
                max_m = 0
                for offset in range(30):
                    r_idx = i + offset
                    if r_idx >= len(rows) or len(rows[r_idx]) <= j or not rows[r_idx][j] or _is_number(rows[r_idx][j]):
                        break
                    num_count = 0
                    for c in range(j + 1, len(rows[r_idx])):
                        if _is_number(rows[r_idx][c]):
                            num_count += 1
                        else:
                            break
                    if num_count > max_m:
                        max_m = num_count
                if max_m >= 2:
                    return pairwise_start, name_col, max_m
    return None, None, None


def parse_pairwise(rows: List[List[str]], pairwise_start: int, name_col: int, max_m: int) -> tuple[List[str], List[List[float]], int]:
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
            if col < len(row):
                try:
                    pairwise[crit_count][j] = _parse_number(row[col])
                except ValueError as e:
                    raise ValueError(f"Ошибка в матрице pairwise, строка {row_idx + 1}, колонка {col + 1}: {e}")
            else:
                pairwise[crit_count][j] = 0.0
        crit_count += 1
        row_idx += 1
    return criteria_names, pairwise, crit_count


def find_alt_header(rows: List[List[str]], pairwise_start: int, m: int) -> tuple[Optional[int], Optional[int]]:
    alt_header_row = alt_start_col = None
    for i in range(pairwise_start + m, len(rows)):
        row = rows[i]
        if len(row) < 2:
            continue
        non_num = [j for j, cell in enumerate(row) if cell and not _is_number(cell)]
        if len(non_num) >= 3:
            non_num.sort()
            current = [non_num[0]]
            best = current[:]
            for k in range(1, len(non_num)):
                if non_num[k] == non_num[k - 1] + 1:
                    current.append(non_num[k])
                else:
                    if len(current) > len(best):
                        best = current
                    current = [non_num[k]]
            if len(current) > len(best):
                best = current
            if len(best) >= 3:
                alt_start_col = best[0]
                alt_header_row = i
                break
    return alt_header_row, alt_start_col


def parse_alternative_names(rows: List[List[str]], alt_header_row: int, alt_start_col: int) -> List[str]:
    alternative_names = []
    row = rows[alt_header_row]
    for j in range(alt_start_col, len(row)):
        cell = row[j]
        if cell and not _is_number(cell) and "Сортировать" not in cell:
            alternative_names.append(cell.strip())
        else:
            break
    if alternative_names and alternative_names[-1] == "Сортировать по возрастанию?":
        alternative_names.pop()
    return alternative_names


def parse_scores(rows: List[List[str]], criteria_names: List[str], data_row_start: int, m: int, n: int) -> List[List[float]]:
    scores = [[0.0] * n for _ in range(m)]
    criteria_found = 0
    for i in range(data_row_start, len(rows)):
        if criteria_found >= m:
            break
        row = rows[i]
        if len(row) < 2:
            continue
        crit_name_expected = criteria_names[criteria_found]
        name_col_scores = None
        for j, cell in enumerate(row):
            if cell.strip() == crit_name_expected:
                name_col_scores = j
                break
        if name_col_scores is None:
            continue
        val_start = name_col_scores + 1
        for alt_idx in range(n):
            col = val_start + alt_idx
            if col < len(row):
                try:
                    scores[criteria_found][alt_idx] = _parse_number(row[col])
                except ValueError as e:
                    raise ValueError(f"Ошибка в матрице scores, строка {i + 1}, колонка {col + 1} (для критерия '{crit_name_expected}'): {e}")
        criteria_found += 1
    if criteria_found < m:
        raise ValueError(f"Нашли только {criteria_found} строк в матрице scores, ожидалось {m}")
    return scores


def parse_sort_asc(rows: List[List[str]], criteria_names: List[str], data_row_start: int, m: int, n: int) -> List[bool]:
    sort_asc = [True] * m
    criteria_found = 0
    for i in range(data_row_start, len(rows)):
        if criteria_found >= m:
            break
        row = rows[i]
        if len(row) < 2:
            continue
        crit_name_expected = criteria_names[criteria_found]
        name_col_scores = None
        for j, cell in enumerate(row):
            if cell.strip() == crit_name_expected:
                name_col_scores = j
                break
        if name_col_scores is None:
            continue
        flag = None
        flag_col = -1
        for col in range(len(row) - 1, name_col_scores, -1):
            if row[col].strip() != "":
                flag = row[col]
                flag_col = col
                break
        if flag is None:
            raise ValueError(
                f"Отсутствует флаг сортировки, строка {i + 1} (для критерия '{crit_name_expected}')"
            )
        if not flag.strip():
            raise ValueError(
                f"Пустое значение флага сортировки, строка {i + 1}, колонка {flag_col + 1} "
                f"(для критерия '{crit_name_expected}')"
            )
        if not _is_number(flag):
            raise ValueError(
                f"Флаг сортировки содержит недопустимые символы, строка {i + 1}, "
                f"колонка {flag_col + 1}: '{flag}'"
            )
        try:
            flag_val = int(_parse_number(flag))
            if flag_val not in (0, 1):
                raise ValueError(
                    f"Флаг сортировки должен быть 0 или 1, найдено {flag_val}"
                )
            sort_asc[criteria_found] = bool(flag_val)
        except ValueError as e:
            raise ValueError(
                f"Ошибка в флаге сортировки, строка {i + 1}, колонка {flag_col + 1} "
                f"(для критерия '{crit_name_expected}'): {e}"
            )
        criteria_found += 1
    return sort_asc


def parse_ahp_csv(csv_text: str) -> Dict[str, Any]:
    """
    Парсит CSV и возвращает сырые данные без финальной валидации.
    Возвращает словарь с ключами:
        m, n, criteria_names, pairwise, alternative_names, scores
    """
    f = StringIO(csv_text.strip())
    reader = csv.reader(f, delimiter=';')
    rows = [[cell.strip().replace('#ДЕЛ/0!', '').replace('#DIV/0!', '') for cell in r]
            for r in reader]

    if len(rows) < 5:
        raise ValueError("CSV слишком короткий")

    pairwise_start, name_col, max_m = find_pairwise_matrix(rows)
    if pairwise_start is None or max_m is None:
        raise ValueError("Не удалось найти матрицу парных сравнений")

    criteria_names, pairwise, m = parse_pairwise(rows, pairwise_start, name_col, max_m)

    alt_header_row, alt_start_col = find_alt_header(rows, pairwise_start, m)
    if alt_header_row is None:
        raise ValueError("Не удалось найти строку с названиями альтернатив")

    alternative_names = parse_alternative_names(rows, alt_header_row, alt_start_col)
    n = len(alternative_names)

    scores = parse_scores(rows, criteria_names, alt_header_row + 1, m, n)
    sort_asc = parse_sort_asc(rows, criteria_names, alt_header_row + 1, m, n)

    return {
        "m": m,
        "n": n,
        "criteria_names": criteria_names,
        "pairwise": pairwise,
        "alternative_names": alternative_names,
        "scores": scores,
        "sort_asc": sort_asc,
    }