from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CARTInput:
    feature_names: list[str]

    X_train: list[list[Any]]
    y_train: list[str]

    X_test: list[list[Any]]
    y_test: list[str]

    X_predict: list[list[Any]]

    max_depth: int = 4
    min_samples_split: int = 2
