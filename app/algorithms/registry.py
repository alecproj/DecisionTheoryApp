from dataclasses import dataclass
from typing import Callable, Any

from app.algorithms.example.schema import validate_input
from app.algorithms.example.algo import run as example_run
from app.algorithms.analytic_hierarchy_process.schema import validator as ahp_validate
from app.algorithms.analytic_hierarchy_process.algo import run as ahp_run


@dataclass(frozen=True)
class AlgorithmMeta:
    id: str
    name: str
    description: str
    guide_link: str
    template_link: str
    validate: Callable[[bytes], Any]
    run: Callable[[Any, Any], None]


ALGORITHMS: dict[str, AlgorithmMeta] = {
    "example": AlgorithmMeta(
        id="example",
        name="Пример (a+b)",
        description=(
            "Учебный алгоритм для демонстрации работы системы. "
            "Принимает на вход CSV-файл с двумя числовыми колонками a и b. "
            "Вычисляет сумму двух чисел и формирует отчёт с результатом. "
            "Используется для проверки корректности загрузки файлов и генерации отчётов. "
            "Не предназначен для решения реальных задач принятия решений."
        ),
        guide_link="/static/guides/example.md",
        template_link="/static/templates/example.csv",
        validate=validate_input,
        run=example_run,
    ),
    "ahp": AlgorithmMeta(
        id="ahp",
        name="Метод анализа иерархий",
        description=(
            "Метод анализа иерархий — это структурированный метод многокритериального принятия решений. "
            "Он позволяет сравнивать альтернативы по нескольким критериям с помощью попарных сравнений. "
            "Каждому критерию и альтернативе присваивается числовой приоритет на основе матриц сравнений. "
            "Метод включает проверку согласованности суждений эксперта через индекс консистентности. "
            "Результатом является ранжированный список альтернатив с указанием итоговых весов."
        ),
        guide_link="/static/guides/ahp.md",
        template_link="/static/templates/ahp.csv",
        validate=ahp_validate,
        run=ahp_run,
    ),
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