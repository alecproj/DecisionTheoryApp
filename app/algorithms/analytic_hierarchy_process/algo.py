from typing import List, Tuple
import numpy as np
from .schema import AHPInput

def calculate_priorities(matrix: List[List[float]]) -> np.ndarray:
    mat = np.array(matrix, dtype=float)

    if mat.ndim != 2 or mat.shape[0] != mat.shape[1]:
        raise ValueError(f"Матрица должна быть квадратной, получено: {mat.shape}")
    if np.any(mat <= 0):
        raise ValueError("Все элементы матрицы должны быть строго положительными")

    eigenvalues, eigenvectors = np.linalg.eig(mat)
    max_index = np.argmax(np.real(eigenvalues))
    raw_vector = eigenvectors[:, max_index]

    if np.max(np.abs(np.imag(raw_vector))) > 1e-6:
        raise ValueError(
            "Собственный вектор содержит значимую мнимую часть — матрица некорректна"
        )

    priorities = np.real(raw_vector)
    priorities = np.abs(priorities)
    priorities /= priorities.sum()
    return priorities

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


def run(input_data: AHPInput, reporter) -> None:

    reporter.h1("Метод анализа иерархий (AHP)")

    # --------------------------------------------------
    # 1. Основные данные
    # --------------------------------------------------

    reporter.h2("Критерии и альтернативы")

    reporter.text("Критерии:")
    for c in input_data.criteria_names:
        reporter.text(f"- {c}")

    reporter.text("\nАльтернативы:")
    for a in input_data.alternative_names:
        reporter.text(f"- {a}")

    # --------------------------------------------------
    # 2. Веса критериев
    # --------------------------------------------------

    reporter.h2("Веса критериев")

    criteria_weights = calculate_priorities(input_data.criteria_pairwise)

    rows = []
    for name, w in zip(input_data.criteria_names, criteria_weights):
        rows.append([name, round(float(w), 4)])

    reporter.table(
        ["Критерий", "Вес"],
        rows
    )

    # --------------------------------------------------
    # 3. Проверка согласованности
    # --------------------------------------------------

    reporter.h2("Оценка согласованности")

    # calculate_consistency возвращает (CI, CR)
    ci, cr = calculate_consistency(
        input_data.criteria_pairwise,
        criteria_weights
    )

    # --------------------------------------------------
    # Теоретическое объяснение
    # --------------------------------------------------

    reporter.text(
        "При использовании метода анализа иерархий важно проверить "
        "согласованность экспертных оценок."
    )

    reporter.text(
        "**Индекс согласованности (CI)** показывает степень отклонения "
        "матрицы парных сравнений от идеально согласованной матрицы."
    )

    reporter.text(
        "**Коэффициент согласованности (CR)** — это отношение индекса "
        "согласованности к случайному индексу. Он показывает, насколько "
        "полученные оценки согласованы по сравнению со случайной матрицей."
    )

    reporter.text("")

    # --------------------------------------------------
    # Значения CI и CR
    # --------------------------------------------------

    reporter.table(
        ["Показатель", "Значение"],
        [
            ["Индекс согласованности (CI)", round(float(ci), 6)],
            ["Коэффициент согласованности (CR)", round(float(cr), 6)],
        ]
    )

    reporter.text("")

    # --------------------------------------------------
    # Таблица интерпретации
    # --------------------------------------------------

    reporter.text("Интерпретация коэффициента согласованности:")
    reporter.text("")
    reporter.table(
        ["CR", "Интерпретация"],
        [
            [" &lt; 0.1", "Хорошая согласованность"],
            ["[0.1; 0.2]", "Допустимая согласованность"],
            [" &gt; 0.2", "Матрица плохо согласована"],
        ]
    )

    reporter.text("")

    # --------------------------------------------------
    # Итоговый вывод
    # --------------------------------------------------

    if cr < 0.1:
        reporter.text(
            f"Полученное значение **CR = {cr:.4f}**, что меньше 0.1. "
            "Следовательно, матрица парных сравнений имеет **хорошую согласованность**, "
            "и результаты анализа можно считать надежными."
        )
    elif cr < 0.2:
        reporter.text(
            f"Полученное значение **CR = {cr:.4f}**, что находится в диапазоне 0.1–0.2. "
            "Согласованность оценок **допустимая**, однако рекомендуется "
            "перепроверить некоторые экспертные сравнения."
        )
    else:
        reporter.text(
            f"Полученное значение **CR = {cr:.4f}**, что превышает 0.2. "
            "Матрица **плохо согласована**, поэтому экспертные оценки "
            "желательно пересмотреть."
        )

    # --------------------------------------------------
    # 4. Глобальная матрица
    # --------------------------------------------------

    reporter.h2("Глобальная матрица")
    local_priorities = [
        calculate_priorities(matrix)
        for matrix in input_data.alternative_pairwise
    ]
    local_matrix = np.array(local_priorities).T
    global_matrix = local_matrix * criteria_weights

    rows = []
    for alt_idx, alt_name in enumerate(input_data.alternative_names):
        row = [alt_name]
        row.extend(round(float(x), 4) for x in global_matrix[alt_idx])
        rows.append(row)

    headers = ["Альтернатива"] + input_data.criteria_names

    reporter.table(headers, rows)

    # --------------------------------------------------
    # 6. Итоговые рейтинги
    # --------------------------------------------------

    reporter.h2("Итоговые рейтинги альтернатив")

    final_scores = global_matrix.sum(axis=1)

    sorted_idx = np.argsort(final_scores)[::-1]

    rows = []
    for i in sorted_idx:
        rows.append([
            input_data.alternative_names[i],
            round(float(final_scores[i]), 4)
        ])

    reporter.table(
        ["Альтернатива", "Итоговый рейтинг"],
        rows
    )

    # --------------------------------------------------
    # 7. Итоговый вывод
    # --------------------------------------------------

    best_idx = sorted_idx[0]
    best_alt = input_data.alternative_names[best_idx]

    reporter.h2("Вывод")

    reporter.text(
        f"Лучшей альтернативой является **{best_alt}**, "
        f"поскольку она имеет наибольший итоговый рейтинг "
        f"**({final_scores[best_idx]:.4f})**."
    )