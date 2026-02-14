from dataclasses import dataclass
from typing import Callable, Any

from app.algorithms.example.schema import validate_input
from app.algorithms.example.algo import run as example_run

@dataclass(frozen=True)
class AlgorithmMeta:
    id: str
    name: str
    validate: Callable[[dict], Any]   # dict -> typed input
    run: Callable[[Any, Any], None]   # (typed input, reporter) -> None

ALGORITHMS: dict[str, AlgorithmMeta] = {
    "example": AlgorithmMeta(
        id="example",
        name="Example (a+b)",
        validate=validate_input,
        run=example_run,
    )
}

def list_algorithms() -> list[dict]:
    return [{"id": m.id, "name": m.name} for m in ALGORITHMS.values()]

def get_algorithm(algorithm_id: str) -> AlgorithmMeta:
    if algorithm_id not in ALGORITHMS:
        raise KeyError(f"Unknown algorithm_id: {algorithm_id}")
    return ALGORITHMS[algorithm_id]
