# schema.py
from dataclasses import dataclass
from typing import List

from parser import parse_ahp_csv   # <-- импорт парсера


@dataclass(frozen=True)
class AHPInput:
    m: int                          # количество критериев
    n: int                          # количество альтернатив
    criteria_names: List[str]
    pairwise: List[List[float]]
    alt_names: List[str]
    scores: List[List[float]]       # [критерий][альтернатива]


def validate_input(data: dict) -> AHPInput:
    """Точка входа — как было раньше"""
    if "csv" not in data:
        raise ValueError("Обязательное поле: csv (содержимое CSV-файла)")

    csv_text = str(data["csv"]).strip()
    if not csv_text:
        raise ValueError("CSV пустой")

    # Парсим
    parsed = parse_ahp_csv(csv_text)

    m = parsed["m"]
    n = parsed["n"]

    if m > 19:
        raise ValueError("Количество критериев превышает 19")
    if n > 19:
        raise ValueError("Количество альтернатив превышает 19")
    if m == 0 or n == 0:
        raise ValueError("Не найдены критерии или альтернативы")

    # Нормализация матрицы парных сравнений
    pairwise = parsed["pairwise"]
    for i in range(m):
        if pairwise[i][i] == 0.0:
            pairwise[i][i] = 1.0
        for j in range(i + 1, m):
            a = pairwise[i][j]
            b = pairwise[j][i]
            if a > 0 and b == 0:
                pairwise[j][i] = 1.0 / a
            elif b > 0 and a == 0:
                pairwise[i][j] = 1.0 / b

    return AHPInput(
        m=m,
        n=n,
        criteria_names=parsed["criteria_names"],
        pairwise=pairwise,
        alt_names=parsed["alt_names"],
        scores=parsed["scores"],
    )