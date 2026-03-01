# ahp.py
from typing import List, Dict, Tuple
import numpy as np

from schema import AHPInput


def calculate_priorities(matrix: List[List[float]]) -> np.ndarray:
    """
    Вычисляет приоритеты из матрицы парных сравнений с помощью метода собственного вектора.
    Возвращает нормализованный собственный вектор.
    """
    mat = np.array(matrix)
    eigenvalues, eigenvectors = np.linalg.eig(mat)
    max_eig_idx = np.argmax(np.abs(eigenvalues))
    priorities = np.abs(eigenvectors[:, max_eig_idx])
    priorities /= priorities.sum()
    return priorities


def calculate_consistency(matrix: List[List[float]], priorities: np.ndarray) -> Tuple[float, float]:
    """
    Вычисляет индекс согласованности (CI) и коэффициент согласованности (CR).
    RI - случайный индекс для матриц размера n (таблица Саати).
    """
    n = len(matrix)
    mat = np.array(matrix)
    lambda_max = np.dot(mat, priorities).max() / priorities.max() if priorities.max() != 0 else n
    CI = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    RI_TABLE = [0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41, 1.45, 1.49, 1.51, 1.48, 1.56, 1.57, 1.59, 1.6, 1.61, 1.62, 1.63, 1.64]
    RI = RI_TABLE[n - 1] if n <= len(RI_TABLE) else 1.64  # approx for larger
    CR = CI / RI if RI != 0 else 0.0
    return CI, CR


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


def run_ahp(input: AHPInput) -> Dict[str, any]:
    """
    Полная реализация AHP:
    - Рассчитывает веса критериев.
    - Генерирует матрицы парных сравнений альтернатив.
    - Рассчитывает локальные приоритеты альтернатив.
    - Рассчитывает глобальные приоритеты и итоговый рейтинг.
    - Выводит таблицу с рейтингом альтернатив, отсортированную по убыванию.
    - Возвращает словарь с результатами (веса, локальные/глобальные приоритеты, рейтинги).
    """
    # 1. Веса критериев из pairwise
    criteria_weights = calculate_priorities(input.pairwise)
    _, cr_criteria = calculate_consistency(input.pairwise, criteria_weights)
    if cr_criteria > 0.1:
        print("Warning: Матрица критериев несогласованна (CR = {:.3f} > 0.1)".format(cr_criteria))

    # 2. Матрицы парных сравнений альтернатив
    alternative_pairwise = generate_alternative_pairwise(input)

    # 3. Локальные приоритеты альтернатив по каждому критерию
    local_priorities = []  # list of n-vectors
    cr_alts = []
    for k in range(input.m):
        priorities = calculate_priorities(alternative_pairwise[k])
        local_priorities.append(priorities)
        _, cr = calculate_consistency(alternative_pairwise[k], priorities)
        cr_alts.append(cr)
        if cr > 0.1:
            print(f"Warning: Матрица альтернатив для критерия {input.criteria_names[k]} несогласованна (CR = {cr:.3f} > 0.1)")

    # 4. Глобальные приоритеты: локальные * веса критериев (n x m matrix)
    global_priorities = np.array(local_priorities).T * criteria_weights  # n x m

    # 5. Итоговый рейтинг: сумма по строкам (n vector)
    ratings = global_priorities.sum(axis=1)

    # 6. Сортировка по убыванию
    sorted_indices = np.argsort(ratings)[::-1]
    sorted_alts = [input.alternative_names[i] for i in sorted_indices]
    sorted_ratings = [ratings[i] for i in sorted_indices]

    # Вывод таблицы
    print("\nИтоговый рейтинг альтернатив (отсортировано по убыванию):")
    print("{:<20} {:<10}".format("Альтернатива", "Рейтинг"))
    print("-" * 30)
    for alt, rating in zip(sorted_alts, sorted_ratings):
        print("{:<20} {:.4f}".format(alt, rating))

    return {
        "criteria_weights": criteria_weights.tolist(),
        "local_priorities": [p.tolist() for p in local_priorities],
        "global_priorities": global_priorities.tolist(),
        "ratings": ratings.tolist(),
        "cr_criteria": cr_criteria,
        "cr_alts": cr_alts
    }