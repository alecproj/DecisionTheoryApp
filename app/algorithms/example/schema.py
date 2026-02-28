# schema.py
from dataclasses import dataclass
from typing import List, Dict, Any
import math

from parser import parse_ahp_csv   # <-- импорт парсера


@dataclass(frozen=True)
class AHPInput:
    m: int                          # количество критериев
    n: int                          # количество альтернатив
    criteria_names: List[str]
    pairwise: List[List[float]]
    alternative_names: List[str]
    scores: List[List[float]]       # [критерий][альтернатива]


def validate_input(data: dict) -> AHPInput:
    """Точка входа — как было раньше"""
    if "csv" not in data:
        raise ValueError("Обязательное поле: csv (содержимое CSV-файла)")

    csv_text = str(data["csv"]).strip()
    if not csv_text:
        raise ValueError("CSV пустой")

    # Парсим
    parsed: Dict[str, Any] = parse_ahp_csv(csv_text)

    m = parsed["m"]
    n = parsed["n"]

    # Базовые проверки размеров
    if m > 19:
        raise ValueError("Количество критериев превышает 19")
    if n > 19:
        raise ValueError("Количество альтернатив превышает 19")
    if m == 0 or n == 0:
        raise ValueError("Не найдены критерии или альтернативы")

    criteria_names = parsed["criteria_names"]
    alternative_names = parsed["alternative_names"]
    pairwise = parsed["pairwise"]
    scores = parsed["scores"]

    # Проверка на отсутствие букв/некорректных значений (все элементы должны быть float без NaN/inf)
    def validate_matrix(matrix, name, allow_zero=True, allow_negative=False):
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

    # Валидация pairwise
    validate_matrix(pairwise, "pairwise", allow_zero=False, allow_negative=False)  # все >0, no neg/NaN

    # Нормализация и специальные проверки для pairwise
    for i in range(m):
        if pairwise[i][i] != 1.0:
            raise ValueError(f"Диагональный элемент в pairwise [{i}][{i}] не равен 1.0: {pairwise[i][i]}")
        for j in range(i + 1, m):
            a = pairwise[i][j]
            b = pairwise[j][i]
            # Проверка верхнетреугольной: целые 1-20
            if a != 0 and (not a.is_integer() or not 1 <= a <= 20):
                raise ValueError(f"Верхнетреугольный элемент pairwise [{i}][{j}] не целое от 1 до 20: {a}")
            if b != 0 and (not 0 < b <= 20):
                raise ValueError(f"Нижнетреугольный элемент pairwise [{j}][{i}] не положительное: {b}")
            if a > 0 and b == 0:
                pairwise[j][i] = 1.0 / a
            elif b > 0 and a == 0:
                pairwise[i][j] = 1.0 / b
            elif a > 0 and b > 0 and abs(b - 1.0 / a) > 1e-6:
                raise ValueError(f"Несоответствие в pairwise [{i}][{j}] и [{j}][{i}]: {a} и {b} не обратны")

    # Валидация scores
    validate_matrix(scores, "scores", allow_zero=True, allow_negative=True)  # allow 0/neg по шаблону (neg values in CSV)

    # Проверка полноты: все строки в scores заполнены (no all-zero rows)
    for i in range(m):
        if all(val == 0 for val in scores[i]):
            raise ValueError(f"Строка {i} в scores полностью нулевая — критерий не заполнен")

    # Другие: уникальность имен optional
    if len(set(criteria_names)) != m:
        # warn: print("Warning: Дубликаты в criteria_names")
        pass
    if len(set(alternative_names)) != n:
        pass

    # Если нужно CR, но это compute-heavy, optional (require numpy?)
    # import numpy as np
    # eigenvalues = np.linalg.eigvals(pairwise)
    # lambda_max = max(eigenvalues.real)
    # CI = (lambda_max - m) / (m - 1)
    # RI = {1:0,2:0,...19:random index table}
    # CR = CI / RI[m]
    # if CR > 0.1: raise or warn

    return AHPInput(
        m=m,
        n=n,
        criteria_names=criteria_names,
        pairwise=pairwise,
        alternative_names=alternative_names,
        scores=scores,
    )