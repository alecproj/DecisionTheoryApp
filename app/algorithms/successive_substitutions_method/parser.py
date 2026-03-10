import csv
import math
import re
from dataclasses import dataclass
from io import StringIO
from typing import List, Optional, Tuple
from sympy import symbols, sympify, SympifyError


# ==========================================================
# СТРУКТУРЫ СЫРЫХ ДАННЫХ
# ==========================================================

@dataclass
class RawTargetFunction:
    function_str: str
    right_part_str: str
    is_max_str: str
    concession_str: str

@dataclass
class RawConstraintFunction:
    function_str: str
    sign_str: str
    right_part_str: str

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

def _normalize_function_str(expr: str) -> str:
    """
    Приводит строку вида '2x1+x2-3x3' к виду '2*x1+x2-3*x3',
    понятному для sympy.
    """
    return re.sub(r'(\d)(x)', r'\1*\2', expr)

# ==========================================================
# ЧТЕНИЕ CSV
# ==========================================================

def read_csv(csv_text: str) -> List[List[str]]:
    f = StringIO(csv_text.strip())
    reader = csv.reader(f, delimiter=';')
    rows = [
        [cell.strip().replace('#ДЕЛ/0!', '').replace('#DIV/0!', '') for cell in r]
        for r in reader
    ]
    return rows

# ==========================================================
# ВАЛИДАЦИЯ ШАБЛОНА И РАЗМЕРОВ
# ==========================================================

def validate_template(rows: List[List[str]]) -> None:
    """
    Проверяет наличие сигнатуры шаблона.
    В нашем случае сигнатура — 'CSM' в ячейках A1, B17 и F39.
    """
    sig_cells = [
        (0, 0),   # A1
        (16, 1),   # B17
        (38, 5),  # F39
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
    if restrictions_cnt > 20:
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
def parse_variable_cnt(rows: List[List[str]]) -> int:
    """
    Читает количество переменных из ячейки F3 (индекс [2][5]).
    Возвращает сырое целое число без валидации диапазона.
    """
    try:
        cell = rows[2][5]
    except IndexError:
        raise ValueError("Ячейка F3 отсутствует в CSV")
    if not cell.strip():
        raise ValueError("Ячейка F3 (количество переменных) пуста")
    if not _is_number(cell):
        raise ValueError(f"Ячейка F3 должна содержать число, получено: '{cell}'")
    value = _parse_number(cell)
    if value != int(value):
        raise ValueError(f"Количество переменных должно быть целым числом, получено: '{cell}'")
    return int(value)

def parse_target_functions_params()  -> None:
    '''
    parse_target_functions_params - передать в функцию только ячейки из диапазона C11:F12 и строчка ниже С13-E13(не весь шаблон)
    и в ответ получить какую-нибудь структуру данных с непровалидированными данными.
    '''

def validate_target_functions_params()
    '''
    передать в функцию полученную на прошлом шаге структуру данных и проверить пользовательский ввод, 
    прогнать каждую функцию через sympy и проверить, 
    что количество переменных в каждой функции соответствует заявленному. 
    Вернуть bool или другую структуру данных с готовыми параметрами для входа в алгоритм.
    '''

def parse_constraint_functions_params() -> None
    '''
    аналогично с целевыми функциями передаем только диапазон C20:E39, не весь шаблон. Аналогично получаем структуру с непровалидированными параметрами.
    '''

def validate_constraint_functions_params()
    '''
    аналогично с целевыми функциями
    '''

def prepare_input_data()
    '''
    если требуется итоговая подготовка входных данных для алгоритма 
    (Возвращает структуру входных данных алгоритма).
    '''

def validate_input_data()
    '''
    полная валидация входных данных по условиям алгоритма. 
    Проверить то, что еще не проверено с точки зрения логики входных данных, 
    а не пользовательского ввода.
    '''