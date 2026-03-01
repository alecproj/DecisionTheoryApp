# ahp.py
from typing import List
from schema import AHPInput


def generate_alternative_pairwise(input: AHPInput) -> List[List[List[float]]]:
    """
    Генерирует m матриц парных сравнений альтернатив по каждому критерию на основе scores.
    Учитывает sort_asc: если ascending (True), ratio = val_i / val_j (больше лучше); если descending (False), ratio = val_j / val_i (меньше лучше).
    Обработка нулевых: если val_j == 0, error.
    """
    alternative_pairwise = [[[0.0 for _ in range(input.n)] for _ in range(input.n)] for _ in range(input.m)]

    for k in range(input.m):  # По критерию
        is_asc = input.sort_asc[k]
        for i in range(input.n):
            alternative_pairwise[k][i][i] = 1.0  # Диагональ
            for j in range(i + 1, input.n):
                val_i = input.scores[k][i]
                val_j = input.scores[k][j]
                if val_j == 0 or val_i == 0:
                    raise ValueError(f"Нулевое значение в scores[{k}][{j}] или [{k}][{i}] — нельзя делить")
                if is_asc:
                    ratio = val_i / val_j
                else:
                    ratio = val_j / val_i
                alternative_pairwise[k][i][j] = ratio
                alternative_pairwise[k][j][i] = 1.0 / ratio if ratio != 0 else 0.0

    return alternative_pairwise


def run_ahp(input: AHPInput) -> AHPInput:
    """
    Рассчитывает m матриц сравнения альтернатив и возвращает обновлённый AHPInput с заполненным alternative_pairwise.
    (Поскольку dataclass frozen, возвращаем новый экземпляр.)
    """
    alternative_pairwise = generate_alternative_pairwise(input)
    return AHPInput(
        m=input.m,
        n=input.n,
        criteria_names=input.criteria_names,
        pairwise=input.pairwise,
        alternative_names=input.alternative_names,
        scores=input.scores,
        sort_asc=input.sort_asc,
        alternative_pairwise=alternative_pairwise
    )