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
        if rows[r][c].strip() != "CSM":
            raise ValueError(f"Неверный шаблон CSV — сигнатура не найдена в ячейке {r+1},{c+1}")

def validate_sizes(variable_cnt: int, targetfunction_cnt: int, restrictions_cnt: int, concession_cnt: int) -> None:
    if variable_cnt > 5:
        raise ValueError("Количество переменных превышает 5")
    if targetfunction_cnt > 3:
        raise ValueError("Количество целевых функций превышает 3")
    if concession_cnt > 2:
        raise ValueError("Количество уступков превышает 2")
    if restrictions_cnt > 10:
        raise ValueError("Количество ограничений превышает 10")

    if variable_cnt == 0:
        raise ValueError("Не найдены переменные")
    if targetfunction_cnt == 0:
        raise ValueError("Не найдены целевые функции")
    if concession_cnt == 0:
        raise ValueError("Не найдены уступки")
    if restrictions_cnt == 0:
        raise ValueError("Не найдены ограничения")

# ==========================================================
# ПАРСИНГ
# ==========================================================

def parse_targetfunctions()  -> None:
def parse_extremumtype_targetfunctions() -> None:
def parse_restrictions() -> None:
def parse_concessions() -> None: