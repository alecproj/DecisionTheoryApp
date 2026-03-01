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
<<<<<<< Updated upstream
=======
    sort_asc: List[bool]            # флаги сортировки по возрастанию
    alternative_pairwise: Optional[List[List[List[float]]]] = None  # m матриц парных сравнений альтернатив по критериям (каждая n x n);
>>>>>>> Stashed changes


def validate_sizes(m: int, n: int) -> None:
    if m > 19:
        raise ValueError("Количество критериев превышает 19")
    if n > 19:
        raise ValueError("Количество альтернатив превышает 19")
    if m == 0 or n == 0:
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


def normalize_and_validate_pairwise(pairwise: List[List[float]], m: int) -> None:
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


def validate_scores(scores: List[List[float]], m: int) -> None:
    validate_matrix(scores, "scores", allow_zero=True, allow_negative=True)
    for i in range(m):
        if all(val == 0 for val in scores[i]):
            raise ValueError(f"Строка {i} в scores полностью нулевая — критерий не заполнен")


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
    criteria_names = parsed["criteria_names"]
    pairwise = parsed["pairwise"]
    alternative_names = parsed["alternative_names"]
    scores = parsed["scores"]

    validate_sizes(m, n)
    validate_matrix(pairwise, "pairwise", allow_zero=False, allow_negative=False)
    normalize_and_validate_pairwise(pairwise, m)
    validate_scores(scores, m)

    # Другие: уникальность имен optional
    if len(set(criteria_names)) != m:
        pass  # warn if needed
    if len(set(alternative_names)) != n:
        pass

    return AHPInput(
        m=m,
        n=n,
        criteria_names=criteria_names,
        pairwise=pairwise,
        alternative_names=alternative_names,
        scores=scores,
<<<<<<< Updated upstream
=======
        sort_asc=parsed["sort_asc"],
        alternative_pairwise=None
>>>>>>> Stashed changes
    )