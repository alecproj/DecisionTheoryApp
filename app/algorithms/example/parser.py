# parser.py
import csv
from io import StringIO
from typing import Dict, Any


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

    # ====================== 1. Поиск и парсинг матрицы парных сравнений ======================
    pairwise_start = name_col = max_m = None

    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if not cell or _is_number(cell):
                continue
            # считаем последовательные числа справа (без пробелов)
            numbers_right = 0
            for k in range(j + 1, len(row)):
                if _is_number(row[k]):
                    numbers_right += 1
                else:
                    break
            if numbers_right >= 3 and i + 1 < len(rows) and len(rows[i + 1]) > j and rows[i + 1][j] and not _is_number(rows[i + 1][j]):
                pairwise_start = i
                name_col = j
                # определяем размер m как max последовательных чисел справа
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
                    break
        if pairwise_start is not None:
            break

    if pairwise_start is None or max_m is None:
        raise ValueError("Не удалось найти матрицу парных сравнений")

    # Сбор критериев и матрицы
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

    m = crit_count

    # ====================== 2. Поиск блока альтернатив ======================
    alt_header_row = alt_start_col = None
    for i in range(pairwise_start + m, len(rows)):
        row = rows[i]
        if len(row) < 2:
            continue
        non_num = [j for j, cell in enumerate(row) if cell and not _is_number(cell)]
        if len(non_num) >= 3:
            # ищем самую длинную последовательную группу
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

    if alt_header_row is None:
        raise ValueError("Не удалось найти строку с названиями альтернатив")

    # Сбор названий альтернатив
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

    n = len(alternative_names)

    # ====================== 3. Сбор оценок (scores) ======================
    scores = [[0.0] * n for _ in range(m)]
    data_row_start = alt_header_row + 1
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

    return {
        "m": m,
        "n": n,
        "criteria_names": criteria_names,
        "pairwise": pairwise,
        "alternative_names": alternative_names,
        "scores": scores,
    }