from __future__ import annotations

from typing import Sequence

import numpy as np

from app.reporting.reporter import MarkdownReporter
from .schema import CriterionResult, DUUInput, Mode


def _format_number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _resolve_strategy_names(input_data: DUUInput, rows_count: int) -> list[str]:
    if input_data.strategy_names is not None:
        return list(input_data.strategy_names)
    return [f"A{i + 1}" for i in range(rows_count)]


def _resolve_state_names(input_data: DUUInput, cols_count: int) -> list[str]:
    if input_data.state_names is not None:
        return list(input_data.state_names)
    return [f"S{j + 1}" for j in range(cols_count)]


def _wald(matrix: np.ndarray, mode: Mode, strategy_names: Sequence[str]) -> CriterionResult:
    if mode == "max":
        scores = matrix.min(axis=1)
        best_index = int(np.argmax(scores))
        explanation = (
            "Для каждой стратегии берётся минимальный выигрыш, "
            "после чего выбирается стратегия с максимальным из этих минимумов."
        )
    else:
        scores = matrix.max(axis=1)
        best_index = int(np.argmin(scores))
        explanation = (
            "Для каждой стратегии берутся максимальные затраты, "
            "после чего выбирается стратегия с минимальным из этих максимумов."
        )

    return CriterionResult(
        criterion="Вальда",
        scores=scores,
        best_index=best_index,
        best_strategy=strategy_names[best_index],
        best_value=float(scores[best_index]),
        explanation=explanation,
    )


def _savage(matrix: np.ndarray, mode: Mode, strategy_names: Sequence[str]) -> CriterionResult:
    if mode == "max":
        best_per_state = matrix.max(axis=0)
        regret_matrix = best_per_state - matrix
        scores = regret_matrix.max(axis=1)
        best_index = int(np.argmin(scores))
        explanation = (
            "Строится матрица сожалений как разность между лучшим выигрышем "
            "в каждом состоянии природы и текущим значением. "
            "Выбирается стратегия с минимальным максимальным сожалением."
        )
    else:
        best_per_state = matrix.min(axis=0)
        regret_matrix = matrix - best_per_state
        scores = regret_matrix.max(axis=1)
        best_index = int(np.argmin(scores))
        explanation = (
            "Строится матрица сожалений как разность между текущими затратами "
            "и минимальными затратами в каждом состоянии природы. "
            "Выбирается стратегия с минимальным максимальным сожалением."
        )

    return CriterionResult(
        criterion="Сэвиджа",
        scores=scores,
        best_index=best_index,
        best_strategy=strategy_names[best_index],
        best_value=float(scores[best_index]),
        explanation=explanation,
        extra_matrix=regret_matrix,
        extra_matrix_title="Матрица сожалений",
    )


def _hurwicz(
    matrix: np.ndarray,
    mode: Mode,
    alpha: float,
    strategy_names: Sequence[str],
) -> CriterionResult:
    row_mins = matrix.min(axis=1)
    row_maxs = matrix.max(axis=1)

    if mode == "max":
        scores = alpha * row_maxs + (1.0 - alpha) * row_mins
        best_index = int(np.argmax(scores))
        explanation = (
            "Для каждой стратегии вычисляется взвешенная оценка между "
            "лучшим и худшим выигрышем. "
            f"Используется alpha = {_format_number(alpha)}."
        )
    else:
        scores = alpha * row_mins + (1.0 - alpha) * row_maxs
        best_index = int(np.argmin(scores))
        explanation = (
            "Для каждой стратегии вычисляется взвешенная оценка между "
            "минимальными и максимальными затратами. "
            f"Используется alpha = {_format_number(alpha)}."
        )

    return CriterionResult(
        criterion="Гурвица",
        scores=scores,
        best_index=best_index,
        best_strategy=strategy_names[best_index],
        best_value=float(scores[best_index]),
        explanation=explanation,
    )


def _add_matrix_table(
    reporter: MarkdownReporter,
    title: str,
    matrix: np.ndarray,
    row_names: Sequence[str],
    col_names: Sequence[str],
) -> None:
    reporter.h2(title)
    headers = ["Стратегия / Состояние"] + list(col_names)
    rows = []

    for i, row_name in enumerate(row_names):
        rows.append(
            [row_name] + [_format_number(float(matrix[i, j])) for j in range(matrix.shape[1])]
        )

    reporter.table(headers, rows)


def _add_result_section(
    reporter: MarkdownReporter,
    result: CriterionResult,
    strategy_names: Sequence[str],
    state_names: Sequence[str],
) -> None:
    reporter.h2(f"Критерий {result.criterion}")
    reporter.text(result.explanation)

    score_rows = []
    for i, strategy_name in enumerate(strategy_names):
        label = strategy_name
        if i == result.best_index:
            label = f"{strategy_name} ← лучшая"
        score_rows.append([label, _format_number(float(result.scores[i]))])

    reporter.table(
        headers=["Стратегия", "Оценка"],
        rows=score_rows,
    )

    reporter.text(
        f"Оптимальная стратегия по критерию {result.criterion}: "
        f"**{result.best_strategy}**, "
        f"значение критерия = **{_format_number(result.best_value)}**."
    )

    if result.extra_matrix is not None and result.extra_matrix_title is not None:
        _add_matrix_table(
            reporter=reporter,
            title=result.extra_matrix_title,
            matrix=result.extra_matrix,
            row_names=strategy_names,
            col_names=state_names,
        )


def run(input_data: DUUInput, reporter: MarkdownReporter) -> None:
    matrix = np.asarray(input_data.payoff_matrix, dtype=float)

    rows_count, cols_count = matrix.shape
    strategy_names = _resolve_strategy_names(input_data, rows_count)
    state_names = _resolve_state_names(input_data, cols_count)

    wald_result = _wald(matrix, input_data.mode, strategy_names)
    savage_result = _savage(matrix, input_data.mode, strategy_names)
    hurwicz_result = _hurwicz(matrix, input_data.mode, input_data.alpha, strategy_names)

    reporter.h1("Решение игры с природой")
    reporter.text(
        "Рассматривается задача принятия решений в условиях неопределённости "
        "без заданных вероятностей состояний природы."
    )
    reporter.text(
        f"Режим оптимизации: "
        f"{'максимизация выигрыша' if input_data.mode == 'max' else 'минимизация затрат'}."
    )
    reporter.text(f"Коэффициент Гурвица: {_format_number(input_data.alpha)}.")

    _add_matrix_table(
        reporter=reporter,
        title="Платёжная таблица",
        matrix=matrix,
        row_names=strategy_names,
        col_names=state_names,
    )

    _add_result_section(
        reporter=reporter,
        result=wald_result,
        strategy_names=strategy_names,
        state_names=state_names,
    )
    _add_result_section(
        reporter=reporter,
        result=savage_result,
        strategy_names=strategy_names,
        state_names=state_names,
    )
    _add_result_section(
        reporter=reporter,
        result=hurwicz_result,
        strategy_names=strategy_names,
        state_names=state_names,
    )

    reporter.h2("Итог")
    reporter.table(
        headers=["Критерий", "Лучшая стратегия", "Значение"],
        rows=[
            ["Вальда", wald_result.best_strategy, _format_number(wald_result.best_value)],
            ["Сэвиджа", savage_result.best_strategy, _format_number(savage_result.best_value)],
            ["Гурвица", hurwicz_result.best_strategy, _format_number(hurwicz_result.best_value)],
        ],
    )


if __name__ == "__main__":
    input_data = DUUInput(
        payoff_matrix=[
            [5, 2, 1],
            [3, 4, 2],
            [6, 1, 0],
        ],
        mode="max",
        alpha=0.6,
        strategy_names=["A1", "A2", "A3"],
        state_names=["S1", "S2", "S3"],
    )

    reporter = MarkdownReporter()
    run(input_data, reporter)
    print(reporter.get_markdown())
