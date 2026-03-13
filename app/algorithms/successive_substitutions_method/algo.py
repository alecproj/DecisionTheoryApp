from typing import List, Tuple
import numpy as np
from scipy.optimize import linprog

from .schema import CSMInput


# ==========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================================================

def _solve_step(
    func: List[float],
    extremum: str,
    A_ub: List[List[float]], # Матрица коэффициентов левых частей ограничений вида <=
    b_ub: List[float],       # Вектор правых частей тех же ограничений
    variable_cnt: int,
) -> Tuple[float, List[float]]:
    """
    Решает одну задачу линейного программирования симплекс-методом.
    Возвращает (значение целевой функции, вектор переменных).
    linprog минимизирует — для max отрицаем коэффициенты.
    """
    bounds = [(0, None)] * variable_cnt

    if extremum == "max":
        c = [-coef for coef in func]
    else:
        c = list(func)

    result = linprog(
        c,
        A_ub=A_ub if A_ub else None,
        b_ub=b_ub if b_ub else None,
        bounds=bounds,
        method='highs',
    )

    if result.status != 0:
        raise ValueError(f"Симплекс-метод не нашёл решения: {result.message}")

    z_value = -result.fun if extremum == "max" else result.fun
    return z_value, list(result.x)


def _build_concession_row(
    func: List[float],
    extremum: str,
    z_optimal: float,
    delta: float,
) -> Tuple[List[float], float]:
    """
    Формирует строку ограничения-уступки для добавления в A_ub / b_ub.
    Всё приводится к виду <= для linprog.

    max: Z >= z* - δ  →  -Z <= -(z* - δ)
    min: Z <= z* + δ  →   Z <=  z* + δ
    """
    if extremum == "max":
        return [-coef for coef in func], -(z_optimal - delta)
    else:
        return list(func), z_optimal + delta


# ==========================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ==========================================================

def run(input_data: CSMInput, reporter) -> None:

    reporter.h1("Метод последовательных уступок (МПУ)")

    # --------------------------------------------------
    # 1. Основные данные
    # --------------------------------------------------

    reporter.h2("Исходные данные")

    reporter.text(f"Количество переменных: **{input_data.variable_cnt}**")
    reporter.text("")
    reporter.text(f"Количество целевых функций: **{input_data.targetfunction_cnt}**")
    reporter.text("")
    reporter.text(f"Количество ограничений: **{input_data.restriction_cnt}**")

    reporter.text("\nЦелевые функции:")
    var_names = [f"x{i+1}" for i in range(input_data.variable_cnt)]

    for i, (func, extremum, ) in enumerate(
        zip(input_data.targetfunctions, input_data.extremumtype_targetfunctions)
    ):
        terms = []
        for coef, var in zip(func, var_names):
            if coef == 0:
                continue
            terms.append(f"{coef:+g}{var}" if terms else f"{coef:g}{var}")
        expr = " ".join(terms) if terms else "0"
        reporter.text(f"- Z{i+1} = {expr} → {extremum}")

    reporter.text("\nУступки:")
    for i, delta in enumerate(input_data.concessions):
        reporter.text(f"- δ{i+1} = {delta}")

    # --------------------------------------------------
    # 2. Подготовка ограничений
    # --------------------------------------------------

    # Базовые ограничения из CSMInput (уже в форме <=)
    base_A_ub = [row[:-1] for row in input_data.restrictions]
    base_b_ub = [row[-1]  for row in input_data.restrictions]

    # Накапливаемые ограничения-уступки
    extra_A_ub: List[List[float]] = []
    extra_b_ub: List[float] = []

    step_results: List[Tuple[float, List[float]]] = []

    # --------------------------------------------------
    # 3. Последовательная оптимизация
    # --------------------------------------------------

    reporter.h2("Последовательная оптимизация")

    for i in range(input_data.targetfunction_cnt):
        func     = input_data.targetfunctions[i]
        extremum = input_data.extremumtype_targetfunctions[i]
        is_last  = (i == input_data.targetfunction_cnt - 1)

        A_ub = base_A_ub + extra_A_ub
        b_ub = base_b_ub + extra_b_ub

        reporter.h2(f"Шаг {i+1} — оптимизация Z{i+1} ({extremum})")

        # Теоретическое объяснение
        if i == 0:
            reporter.text(
                "На первом шаге оптимизируем главную целевую функцию "
                "на исходной системе ограничений."
            )
        else:
            reporter.text(
                f"На шаге {i+1} оптимизируем Z{i+1} с учётом уступок "
                f"по предыдущим {'функции' if i == 1 else 'функциям'}."
            )

        # Решаем
        try:
            z_optimal, x_optimal = _solve_step(func, extremum, A_ub, b_ub, input_data.variable_cnt)
        except ValueError as e:
            reporter.text(f"**Ошибка на шаге {i+1}:** {e}")
            return

        step_results.append((z_optimal, x_optimal))

        # Таблица результатов шага
        reporter.text("")
        reporter.table(
            ["Переменная", "Значение"],
            [[f"x{j+1}", round(x_optimal[j], 6)] for j in range(input_data.variable_cnt)]
            + [[f"Z{i+1}", round(z_optimal, 6)]]
        )

        # Добавляем ограничение-уступку (кроме последнего шага)
        if not is_last:
            delta = input_data.concessions[i]
            conc_row, conc_rhs = _build_concession_row(func, extremum, z_optimal, delta)
            extra_A_ub.append(conc_row)
            extra_b_ub.append(conc_rhs)

            if extremum == "max":
                bound_value = round(z_optimal - delta, 6)
                reporter.text(
                    f"Добавлено ограничение-уступка: "
                    f"**Z{i+1} ≥ {z_optimal:.4f} − {delta} = {bound_value}**"
                )
            else:
                bound_value = round(z_optimal + delta, 6)
                reporter.text(
                    f"Добавлено ограничение-уступка: "
                    f"**Z{i+1} ≤ {z_optimal:.4f} + {delta} = {bound_value}**"
                )

    # --------------------------------------------------
    # 4. Итоговые значения всех целевых функций
    # --------------------------------------------------

    reporter.h2("Итоговые значения")

    final_x = step_results[-1][1]

    # Пересчитываем все целевые функции на финальных переменных
    final_z_values = []
    for func in input_data.targetfunctions:
        z_val = sum(coef * x for coef, x in zip(func, final_x))
        final_z_values.append(z_val)

    reporter.table(
        ["Показатель", "Значение"],
        [[f"x{j+1}", round(final_x[j], 4)] for j in range(input_data.variable_cnt)]
        + [[f"Z{i+1} ({input_data.extremumtype_targetfunctions[i]})", round(final_z_values[i], 4)]
           for i in range(input_data.targetfunction_cnt)]
    )

    # --------------------------------------------------
    # 5. Вывод
    # --------------------------------------------------

    reporter.h2("Вывод")

    x_str = ", ".join(f"x{j+1} = {round(final_x[j], 4)}" for j in range(input_data.variable_cnt))
    reporter.text(f"Оптимальное решение: **{x_str}**")

    for i, (z_val, extremum) in enumerate(
        zip(final_z_values, input_data.extremumtype_targetfunctions)
    ):
        reporter.text(f"Z{i+1} ({extremum}) = **{round(z_val, 4)}**")