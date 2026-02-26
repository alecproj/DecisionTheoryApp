from dataclasses import dataclass
from typing import Callable, Any

from app.algorithms.example.schema import validate_input
from app.algorithms.example.algo import run as example_run

@dataclass(frozen=True)
class AlgorithmMeta:
    id: str
    name: str
    description: str
    guide_link: str
    template_link: str
    validate: Callable[[dict], Any]   # dict -> typed input
    run: Callable[[Any, Any], None]   # (typed input, reporter) -> None

ALGORITHMS: dict[str, AlgorithmMeta] = {
    "example": AlgorithmMeta(
        id="example", #Идентификатор алгоритма
        name="Addication (a + b)", #Название алгоритма
        description=(
            "Example text description!" #Текст краткого описания алгоритма
        ),
        guide_link="https://example.com/guide", #Ссылка на инструкцию
        template_link="https://example.com/template", #Cсылка на скачивание шаблона
        validate=validate_input, #Функция валидации входных данных
        run=example_run, #Функция запуска алгоритма
    )
}

def list_algorithms() -> list[dict]:
    return [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "guide_link": m.guide_link,
            "template_link": m.template_link,
        }
        for m in ALGORITHMS.values()
    ]

def get_algorithm(algorithm_id: str) -> AlgorithmMeta:
    if algorithm_id not in ALGORITHMS:
        raise KeyError(f"Unknown algorithm_id: {algorithm_id}")
    return ALGORITHMS[algorithm_id]
