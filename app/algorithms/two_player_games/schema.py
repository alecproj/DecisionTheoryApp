from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class TPGInput:
    payoff_matrix_p1: Sequence[Sequence[float]]
    payoff_matrix_p2: Sequence[Sequence[float]]
    row_strategy_names: Sequence[str]
    col_strategy_names: Sequence[str]
