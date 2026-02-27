from dataclasses import dataclass
from typing import List
import csv
from io import StringIO


@dataclass(frozen=True)
class AHPInput:
    m: int
    n: int
    criteria_names: List[str]
    pairwise: List[List[float]]
    alt_names: List[str]
    scores: List[List[float]]       # [критерий][альтернатива]


def _is_number(s: str) -> bool:
    """Проверяет, можно ли строку интерпретировать как число (с запятой или точкой)."""
    if not s or not s.strip():
        return False
    s = s.strip().replace(',', '.')
    try:
        float(s)
        return True
    except ValueError:
        return False


def _parse_number(s: str) -> float:
    """Преобразует строку в число, заменяя запятую на точку."""
    if not s.strip():
        return 0.0
    try:
        return float(s.replace(',', '.'))
    except ValueError:
        return 0.0


def validate_input(data: dict) -> AHPInput:
    if "csv" not in data:
        raise ValueError("Обязательное поле: csv (содержимое CSV-файла)")

    csv_text = str(data["csv"]).strip()
    if not csv_text:
        raise ValueError("CSV пустой")

    f = StringIO(csv_text)
    reader = csv.reader(f, delimiter=';')
    rows = []
    for r in reader:
        # очищаем ячейки от мусорных формул, но оставляем пустые строки как есть
        cleaned = [cell.strip().replace('#ДЕЛ/0!', '').replace('#DIV/0!', '') for cell in r]
        rows.append(cleaned)

    if len(rows) < 5:
        raise ValueError("CSV слишком короткий")

    # ------------------------------------------------------------------
    # 1. Поиск матрицы парных сравнений
    # ------------------------------------------------------------------
    pairwise_start = None
    name_col = None          # индекс колонки, где стоит имя критерия
    max_m = None

    for i, row in enumerate(rows):
        # ищем строку, где есть нечисловая ячейка, а справа от неё несколько чисел
        for j, cell in enumerate(row):
            if not cell or _is_number(cell):
                continue
            # нашли нечисловую ячейку (потенциальное имя)
            # проверим, что справа есть хотя бы два числа
            numbers_right = 0
            for k in range(j+1, len(row)):
                if _is_number(row[k]):
                    numbers_right += 1
                else:
                    break
            if numbers_right >= 3:   # достаточно, чтобы считать началом матрицы
                # проверим также, что в следующих строках в этой же колонке есть непустые значения
                if i+1 < len(rows) and len(rows[i+1]) > j and rows[i+1][j] and not _is_number(rows[i+1][j]):
                    pairwise_start = i
                    name_col = j
                    # определим max_m как максимальное количество чисел справа от имени в этой и следующих строках
                    max_m = 0
                    for offset in range(20):  # ограничим, чтобы не уйти далеко
                        r_idx = i + offset
                        if r_idx >= len(rows):
                            break
                        r = rows[r_idx]
                        if len(r) <= j or not r[j] or _is_number(r[j]):
                            break
                        # считаем числа подряд после name_col
                        num_count = 0
                        for col in range(j+1, len(r)):
                            if _is_number(r[col]):
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
        raise ValueError(
            "Не удалось найти матрицу парных сравнений.\n"
            "Убедитесь, что в CSV есть блок с именами критериев и числами справа от них."
        )

    # ------------------------------------------------------------------
    # 2. Сбор матрицы парных сравнений и имён критериев
    # ------------------------------------------------------------------
    criteria_names = []
    pairwise = [[0.0] * max_m for _ in range(max_m)]

    row_idx = pairwise_start
    crit_count = 0
    while row_idx < len(rows) and crit_count < max_m:
        row = rows[row_idx]
        if len(row) <= name_col or not row[name_col] or _is_number(row[name_col]):
            break

        name = row[name_col].strip()
        criteria_names.append(name)

        # собираем числа из колонок name_col+1 ... name_col+max_m
        for j in range(max_m):
            col = name_col + 1 + j
            if col < len(row) and _is_number(row[col]):
                pairwise[crit_count][j] = _parse_number(row[col])
            else:
                pairwise[crit_count][j] = 0.0

        crit_count += 1
        row_idx += 1

    m = crit_count
    if m != max_m:
        raise ValueError(f"Нашли только {m} строк в матрице критериев, ожидалось {max_m}")
    if m > 19:
        raise ValueError("Количество критериев превышает 19")

    # заполняем диагональ единицами и восстанавливаем обратные значения
    for i in range(m):
        if pairwise[i][i] == 0.0:
            pairwise[i][i] = 1.0
        for j in range(i+1, m):
            a = pairwise[i][j]
            b = pairwise[j][i]
            if a > 0 and b == 0:
                pairwise[j][i] = 1.0 / a if a != 0 else 0.0
            elif b > 0 and a == 0:
                pairwise[i][j] = 1.0 / b if b != 0 else 0.0

    # ------------------------------------------------------------------
    # 3. Поиск блока с альтернативами
    # ------------------------------------------------------------------
    # Ищем строку, в которой много нечисловых ячеек (названия альтернатив)
    alt_header_row = None
    alt_start_col = None
    for i in range(pairwise_start + m, len(rows)):
        row = rows[i]
        if len(row) < 2:
            continue
        non_numeric_indices = [j for j, cell in enumerate(row) if cell and not _is_number(cell)]
        if len(non_numeric_indices) >= 3:
            # Find the longest consecutive group
            if non_numeric_indices:
                non_numeric_indices.sort()
                max_group = []
                current_group = [non_numeric_indices[0]]
                for k in range(1, len(non_numeric_indices)):
                    if non_numeric_indices[k] == non_numeric_indices[k-1] + 1:
                        current_group.append(non_numeric_indices[k])
                    else:
                        if len(current_group) > len(max_group):
                            max_group = current_group
                        current_group = [non_numeric_indices[k]]
                if len(current_group) > len(max_group):
                    max_group = current_group
                if len(max_group) >= 3:
                    alt_start_col = max_group[0]
                    alt_header_row = i
                    break

    if alt_header_row is None:
        raise ValueError("Не удалось найти строку с названиями альтернатив")

    # извлекаем имена альтернатив из строки alt_header_row, начиная с alt_start_col (все consecutive)
    alt_names = []
    row = rows[alt_header_row]
    for j in range(alt_start_col, len(row)):
        cell = row[j]
        if cell and not _is_number(cell) and "Сортировать" not in cell:
            alt_names.append(cell.strip())
        else:
            break  # stop at first number or empty or sort header after start

    # If somehow sort is included, remove it
    if alt_names and alt_names[-1] == "Сортировать по возрастанию?":
        del alt_names[-1]

    n = len(alt_names)
    if n < 1:
        raise ValueError("Не найдены имена альтернатив")
    if n > 19:
        raise ValueError("Количество альтернатив превышает 19")

    # ------------------------------------------------------------------
    # 4. Сбор оценок альтернатив (матрица scores)
    # ------------------------------------------------------------------
    scores = [[0.0] * n for _ in range(m)]

    # после заголовка альтернатив идут строки с данными для каждого критерия
    data_row_start = alt_header_row + 1

    criteria_found = 0
    for i in range(data_row_start, len(rows)):
        if criteria_found >= m:
            break
        row = rows[i]
        if len(row) < 2:
            continue

        crit_idx = criteria_found
        crit_name_expected = criteria_names[crit_idx]

        name_col_scores = None
        for j, cell in enumerate(row):
            if cell.strip() == crit_name_expected:
                name_col_scores = j
                break
        if name_col_scores is None:
            continue

        val_start_scores = name_col_scores + 1

        # собираем значения для альтернатив из колонок val_start_scores ... val_start_scores + n - 1
        # (игнорируем колонку "Сортировать..." дальше)
        for alt_idx in range(n):
            col = val_start_scores + alt_idx
            if col < len(row) and _is_number(row[col]):
                scores[crit_idx][alt_idx] = _parse_number(row[col])
            else:
                scores[crit_idx][alt_idx] = 0.0

        criteria_found += 1

    if criteria_found < m:
        raise ValueError(f"Нашли только {criteria_found} строк в матрице scores, ожидалось {m}")

    # ------------------------------------------------------------------
    # 5. Финальная проверка и возврат
    # ------------------------------------------------------------------
    return AHPInput(
        m=m,
        n=n,
        criteria_names=criteria_names,
        pairwise=pairwise,
        alt_names=alt_names,
        scores=scores,
    )