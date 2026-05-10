from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class FuzzyRelationsInput:
    """
    Входные данные для алгоритма композиции нечетких отношений.

    Схема задачи:
    - R1 задает отношение общего множества Y к множеству X: Y x X.
    - R2 задает отношение общего множества Y к множеству Z: Y x Z.
    - результат алгоритма строится как отношение X x Z.
    """

    y_names: Sequence[str]
    x_names: Sequence[str]
    z_names: Sequence[str]

    # Размерность: len(Y) x len(X)
    r1: Sequence[Sequence[float]]

    # Размерность: len(Y) x len(Z)
    r2: Sequence[Sequence[float]]


def validate_input(file_content: str) -> FuzzyRelationsInput:
    """
    Единая точка входа для валидации и преобразования файла шаблона.

    В registry.py лучше импортировать именно эту функцию:
        from app.algorithms.fuzzy_relations.schema import validate_input

    Сама техническая логика чтения CSV, проверки сигнатур, определения
    размеров матриц и парсинга значений находится в parser.py. Такой вариант
    оставляет schema.py публичным контрактом алгоритма, а parser.py —
    внутренним инфраструктурным модулем.
    """
    from .parser import parse_fuzzy_relations_input

    return parse_fuzzy_relations_input(file_content)
