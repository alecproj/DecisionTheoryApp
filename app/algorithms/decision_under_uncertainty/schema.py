from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np

Mode = Literal["max", "min"]


@dataclass
class DUUInput:
    payoff_matrix: Sequence[Sequence[float]]
    mode: Mode = "max"
    alpha: float = 0.5
    strategy_names: Sequence[str] | None = None
    state_names: Sequence[str] | None = None


@dataclass
class CriterionResult:
    criterion: str
    scores: np.ndarray
    best_index: int
    best_strategy: str
    best_value: float
    explanation: str
    extra_matrix: np.ndarray | None = None
    extra_matrix_title: str | None = None
