from __future__ import annotations

from typing import Sequence

import nashpy as nash
import numpy as np

from app.reporting.reporter import MarkdownReporter
from .schema import TPGInput


def _format_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _is_pure(strategy: np.ndarray, eps: float = 1e-9) -> bool:
    return int(np.sum(strategy > eps)) == 1


def _strategy_type(strategy: np.ndarray, eps: float = 1e-9) -> str:
    active = np.sum(strategy > eps)
    return "чистая" if active == 1 else "смешанная"


def _format_strategy(
    strategy: np.ndarray,
    strategy_names: Sequence[str],
    eps: float = 1e-9,
) -> str:
    active = []

    for prob, name in zip(strategy, strategy_names):
        if prob > eps:
            if abs(prob - 1.0) < eps:
                return name

            active.append(f"{_format_number(prob)} {name}")

    if not active:
        return "нулевая стратегия"

    return ", ".join(active)


def _add_matrix_table(
    reporter: MarkdownReporter,
    title: str,
    matrix: np.ndarray,
    row_names: Sequence[str],
    col_names: Sequence[str],
) -> None:
    reporter.h2(title)
    headers = ["Стратегия \\ Стратегия"] + list(col_names)
    rows = []

    for i, row_name in enumerate(row_names):
        rows.append(
            [row_name] + [_format_number(float(matrix[i, j])) for j in range(matrix.shape[1])]
        )

    reporter.table(headers, rows)


def _payoff_at_equilibrium(
    a: np.ndarray,
    b: np.ndarray,
    sigma_r: np.ndarray,
    sigma_c: np.ndarray,
) -> tuple[float, float]:
    u1 = float(sigma_r @ a @ sigma_c)
    u2 = float(sigma_r @ b @ sigma_c)
    return u1, u2


def run(input_data: TPGInput, reporter: MarkdownReporter) -> None:
    a = np.asarray(input_data.payoff_matrix_p1, dtype=float)
    b = np.asarray(input_data.payoff_matrix_p2, dtype=float)

    row_names = list(input_data.row_strategy_names)
    col_names = list(input_data.col_strategy_names)

    game = nash.Game(a, b)

    equilibria: list[tuple[np.ndarray, np.ndarray]] = []

    try:
        equilibria = list(game.support_enumeration())
    except Exception:
        equilibria = []

    if not equilibria:
        try:
            equilibria = list(game.vertex_enumeration())
        except Exception:
            equilibria = []

    reporter.h1("Решение парной игры")
    reporter.text(
        "Рассматривается парная игра в нормальной форме. "
        "Для поиска равновесий Нэша используется библиотека nashpy."
    )

    is_zero_sum = np.allclose(b, -a)
    reporter.text(
        f"Тип игры: {'антагонистическая (нулевой суммы)' if is_zero_sum else 'биматричная (общего вида)'}."
    )
    reporter.text(f"Размер игры: {a.shape[0]} x {a.shape[1]}.")

    _add_matrix_table(
        reporter=reporter,
        title="Матрица выигрышей игрока 1",
        matrix=a,
        row_names=row_names,
        col_names=col_names,
    )

    _add_matrix_table(
        reporter=reporter,
        title="Матрица выигрышей игрока 2",
        matrix=b,
        row_names=row_names,
        col_names=col_names,
    )

    reporter.h2("Найденные равновесия Нэша")

    if not equilibria:
        reporter.text(
            "Равновесия не найдены стандартными методами support_enumeration и vertex_enumeration."
        )
        return

    summary_rows = []

    for idx, (sigma_r, sigma_c) in enumerate(equilibria, start=1):
        sigma_r = np.asarray(sigma_r, dtype=float)
        sigma_c = np.asarray(sigma_c, dtype=float)

        u1, u2 = _payoff_at_equilibrium(a, b, sigma_r, sigma_c)

        reporter.h2(f"Равновесие {idx}")
        reporter.table(
            headers=["Игрок", "Стратегия", "Тип", "Ожидаемый выигрыш"],
            rows=[
                [
                    "Игрок 1",
                    _format_strategy(
                        sigma_r,
                        row_names,
                    ),
                    _strategy_type(sigma_r),
                    _format_number(u1),
                ],
                [
                    "Игрок 2",
                    _format_strategy(
                        sigma_c,
                        col_names,
                    ),
                    _strategy_type(sigma_c),
                    _format_number(u2),
                ],
            ],
        )
        reporter.text(
            f"Игрок 1 использует {_strategy_type(sigma_r)} стратегию: "
            f"{_format_strategy(sigma_r, row_names)}."
        )

        reporter.text(
            f"Игрок 2 использует {_strategy_type(sigma_c)} стратегию: "
            f"{_format_strategy(sigma_c, col_names)}."
        )

        summary_rows.append(
            [
                str(idx),
                _strategy_type(sigma_r),
                _strategy_type(sigma_c),
                _format_number(u1),
                _format_number(u2),
            ]
        )

    reporter.h2("Итог")
    reporter.table(
        headers=[
            "Равновесие",
            "Игрок 1",
            "Игрок 2",
            "Выигрыш игрока 1",
            "Выигрыш игрока 2",
        ],
        rows=summary_rows,
    )
