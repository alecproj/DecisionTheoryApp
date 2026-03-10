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

def parse_target_functions_params(rows: List[List[str]]) -> List[RawTargetFunction]:
    """
    Читает диапазон C11:F13 (rows[10:13], cols [2:6]).
    Формат строки: функция | правая часть | максимум (0/1) | уступки
    Уступка у последней функции может быть пустой.
    Возвращает список RawTargetFunction с непровалидированными данными.
    """
    cells = [row[2:6] for row in rows[10:13]]
    result = []
    for row_offset, row in enumerate(cells):
        if all(not cell.strip() for cell in row):
            continue
        if len(row) < 4:
            raise ValueError(
                f"Строка {row_offset + 11} содержит меньше 4 колонок "
                f"в блоке целевых функций"
            )
        function_str   = row[0].strip()
        right_part_str = row[1].strip()
        is_max_str     = row[2].strip()
        concession_str = row[3].strip()  # может быть пустой у последней функции
        if not function_str:
            break  # дошли до конца заполненных строк
        result.append(RawTargetFunction(
            function_str=function_str,
            right_part_str=right_part_str,
            is_max_str=is_max_str,
            concession_str=concession_str,
        ))

    return result

def validate_target_functions_params(
    raw: List[RawTargetFunction],
    variable_cnt: int) -> Tuple[List[List[float]], List[str], List[float]]:
    """
    Валидирует сырые данные целевых функций.
    Возвращает кортеж:
      - targetfunctions: List[List[float]] — коэффициенты функций
      - extremumtype: List[str]            — 'max' или 'min' для каждой функции
      - concessions: List[float]           — уступки (N-1 штук)
    """
    valid_symbols = [f"x{i}" for i in range(1, variable_cnt + 1)]

    targetfunctions = []
    extremumtype = []
    concessions = []

    for i, item in enumerate(raw):
        is_last = (i == len(raw) - 1)
        # --- right_part (пока не используется в CSMInput, но валидируем) ---
        if not item.right_part_str:
            raise ValueError(f"Целевая функция {i+1}: правая часть пуста")
        _parse_number(item.right_part_str)  # проверяем что число

        # --- is_max ---
        if item.is_max_str not in ("0", "1"):
            raise ValueError(
                f"Целевая функция {i+1}: поле 'Максимум' должно быть 0 или 1, "
                f"получено: '{item.is_max_str}'"
            )
        extremumtype.append("max" if item.is_max_str == "1" else "min")

        # --- concession ---
        if item.concession_str:
            concessions.append(_parse_number(item.concession_str))
        elif not is_last:
            raise ValueError(
                f"Целевая функция {i+1}: уступка обязательна для всех функций, "
                f"кроме последней"
            )
        # --- function через sympy → коэффициенты ---
        coefficients = _parse_function_to_coefficients(
            item.function_str, valid_symbols, label=f"Целевая функция {i+1}"
        )
        targetfunctions.append(coefficients)
    return targetfunctions, extremumtype, concessions

def parse_constraint_functions_params(rows: List[List[str]]) -> List[RawConstraintFunction]:
    """
    Читает диапазон C20:E39 (rows[19:39], cols [2:5]).
    Формат строки: функция | знак сравнения | правая часть
    Возвращает список RawConstraintFunction с непровалидированными данными.
    """
    cells = [row[2:5] for row in rows[19:39]]
    result = []

    for row_offset, row in enumerate(cells):
        if all(not cell.strip() for cell in row):
            continue

        if len(row) < 3:
            raise ValueError(
                f"Строка {row_offset + 20} содержит меньше 3 колонок "
                f"в блоке ограничений"
            )

        function_str   = row[0].strip()
        sign_str       = row[1].strip()
        right_part_str = row[2].strip()

        if not function_str:
            continue  # пустая строка внутри диапазона — пропускаем

        result.append(RawConstraintFunction(
            function_str=function_str,
            sign_str=sign_str,
            right_part_str=right_part_str,
        ))

    return result

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


# ==========================================================
# ВСПОМОГАТЕЛЬНАЯ УТИЛИТА: ФУНКЦИЯ → КОЭФФИЦИЕНТЫ
# ==========================================================

def _parse_function_to_coefficients(
    function_str: str,
    valid_symbols: List[str],
    label: str = "Функция"
) -> List[float]:
    """
    Парсит строку вида '2x1+x2-3x3' через sympy и возвращает
    список коэффициентов [a1, a2, ..., an] по каждой переменной.
    Проверяет, что функция не содержит недопустимых переменных.
    """
    sym_objects = {s: symbols(s) for s in valid_symbols}
    normalized = _normalize_function_str(function_str)

    try:
        expr = sympify(normalized, locals=sym_objects)
    except SympifyError as e:
        raise ValueError(f"{label}: не удалось разобрать выражение '{function_str}': {e}")

    used_symbols = {str(s) for s in expr.free_symbols}
    invalid = used_symbols - set(valid_symbols)
    if invalid:
        raise ValueError(
            f"{label}: выражение содержит недопустимые переменные {invalid}. "
            f"Допустимы: {valid_symbols}"
        )

    coefficients = []
    for s in valid_symbols:
        coef = expr.coeff(symbols(s))
        coefficients.append(float(coef))

    return coefficients