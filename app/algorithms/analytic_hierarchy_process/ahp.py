from typing import List, Dict, Tuple
import numpy as np

from schema import AHPInput


# ==========================================================
# 1. Базовые вычисления
# ==========================================================

# Вычисление вектора приоритетов методом главного собственного вектора.
# 1. Решается задача Aw = λw
# 2. Находится максимальное собственное число λ_max
# 3. Берётся соответствующий собственный вектор
# 4. Берётся действительная часть (матрица вещественная)
# 5. Вектор нормируется так, чтобы сумма элементов = 1
# Итог: получаем относительные веса (приоритеты)
def calculate_priorities(matrix: List[List[float]]) -> np.ndarray:
    mat = np.array(matrix)
    eigenvalues, eigenvectors = np.linalg.eig(mat)
    max_index = np.argmax(np.real(eigenvalues))
    priorities = np.real(eigenvectors[:, max_index])
    priorities = np.abs(priorities)
    priorities /= priorities.sum()
    return priorities

# Проверка согласованности матрицы парных сравнений.
# 1. Вычисляется λ_max через формулу (Aw)_i / w_i
# 2. Считается индекс согласованности CI
# 3. Вычисляется отношение согласованности CR
# CR показывает степень логической непротиворечивости экспертных оценок.
def calculate_consistency(matrix: List[List[float]],
                          priorities: np.ndarray) -> Tuple[float, float]:
    n = len(matrix)
    mat = np.array(matrix)
    lambda_max = np.real(np.dot(mat, priorities) / priorities).mean()
    CI = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    RI_TABLE = [
        0, 0, 0.58, 0.9, 1.12, 1.24, 1.32, 1.41,
        1.45, 1.49, 1.51, 1.48, 1.56, 1.57,
        1.59, 1.6, 1.61, 1.62, 1.63, 1.64
    ]
    RI = RI_TABLE[n - 1] if n <= len(RI_TABLE) else 1.64
    CR = CI / RI if RI != 0 else 0.0
    return CI, CR

# ==========================================================
# 2. Шаг 1 — критерии
# ==========================================================

# Обработка матрицы критериев:
# 1. Вычисляются веса критериев
# 2. Проверяется согласованность экспертных оценок
# Результат: глобальные веса критериев
def _process_criteria(input: AHPInput):
    weights = calculate_priorities(input.criteria_pairwise)
    _, cr = calculate_consistency(input.criteria_pairwise, weights)
    return weights, cr

# ==========================================================
# 3. Шаг 2 — альтернативы
# ==========================================================

# Для каждого критерия:
# 1. Вычисляется вектор локальных приоритетов альтернатив
# 2. Проверяется согласованность матрицы
# Итог: формируется список локальных весов по каждому критерию
def _process_alternatives(input: AHPInput):
    local_priorities = []
    cr_values = []
    for matrix in input.alternative_pairwise:
        priorities = calculate_priorities(matrix)
        local_priorities.append(priorities)
        _, cr = calculate_consistency(matrix, priorities)
        cr_values.append(cr)
    return local_priorities, cr_values


# ==========================================================
# 4. Шаг 3 — глобальная матрица
# ==========================================================

# построение основной матрицы А(m, n) - Критерии, Альтернативы
# 1. Локальные приоритеты объединяются в матрицу размером (альтернативы × критерии)
# 2. Каждый столбец умножается на вес соответствующего критерия
# Реализуется формула G_ij = L_ij * w_j
def _build_global_matrix(local_priorities: List[np.ndarray],
                         criteria_weights: np.ndarray):
    local_matrix = np.array(local_priorities).T
    global_matrix = local_matrix * criteria_weights
    return global_matrix


# ==========================================================
# 5. Шаг 4 — итоговые рейтинги
# ==========================================================

# Вычисление итогового рейтинга альтернатив.
# Суммирование по строкам глобальной матрицы:
# R_i = Σ_j (L_ij * w_j)
def _calculate_ratings(global_matrix: np.ndarray):
    return global_matrix.sum(axis=1)


# ==========================================================
# 6. Шаг 5 — сортировка
# ==========================================================

# Сортировка альтернатив по убыванию итогового рейтинга.
# Определяет ранжирование альтернатив от лучшей к худшей.
def _sort_alternatives(ratings: np.ndarray,
                       alternative_names: List[str]):
    sorted_indices = np.argsort(ratings)[::-1]
    sorted_names = [alternative_names[i] for i in sorted_indices]
    sorted_values = [float(ratings[i]) for i in sorted_indices]
    return sorted_names, sorted_values

# ==========================================================
# 7. Основной метод
# ==========================================================

# Основной алгоритм метода анализа иерархий (AHP):
def ahp(input: AHPInput) -> Dict[str, any]:

    # Шаг 1 — вычисление весов критериев
    criteria_weights, cr_criteria = _process_criteria(input)
    # Шаг 2 — вычисление локальных приоритетов альтернатив
    local_priorities, cr_alternatives = _process_alternatives(input)
    # Шаг 3 — формирование глобальной модели
    global_matrix = _build_global_matrix(local_priorities,
                                         criteria_weights)
    # Шаг 4 — вычисление итоговых рейтингов
    ratings = _calculate_ratings(global_matrix)
    # Шаг 5 — ранжирование альтернатив
    sorted_names, sorted_values = _sort_alternatives(
        ratings,
        input.alternative_names
    )

    return {
        "criteria_weights": criteria_weights.tolist(),
        "local_priorities": [p.tolist() for p in local_priorities],
        "global_priorities": global_matrix.tolist(),
        "ratings": ratings.tolist(),
        "sorted_alternatives": sorted_names,
        "sorted_ratings": sorted_values,
        "cr_criteria": cr_criteria,
        "cr_alternatives": cr_alternatives
    }