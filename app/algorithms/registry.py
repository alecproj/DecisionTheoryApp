from dataclasses import dataclass
from typing import Callable, Any

from app.algorithms.analytic_hierarchy_process.schema import validator as ahp_validate
from app.algorithms.analytic_hierarchy_process.algo import run as ahp_run

from app.algorithms.successive_substitutions_method.schema import validator as csm_validate
from app.algorithms.successive_substitutions_method.algo import run as csm_run

from app.algorithms.two_player_games.parser import validate_input as tpg_validate
from app.algorithms.two_player_games.algo import run as tpg_run

from app.algorithms.decision_under_uncertainty.parser import validate_input as duu_validate
from app.algorithms.decision_under_uncertainty.algo import run as duu_run

from app.algorithms.cart.parser import validate_input as cart_validate
from app.algorithms.cart.algo import run as cart_run


@dataclass(frozen=True)
class AlgorithmMeta:
    id: str
    name: str
    description: str
    guide_link: str
    template_link: str
    validate: Callable[[str], Any]
    run: Callable[[Any, Any], None]


ALGORITHMS: dict[str, AlgorithmMeta] = {
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
        guide_link="https://e.pcloud.link/publink/show?code=kZzCRGZR8MswbjXsJ4BmLwKhK7Uluo5sufk",
        template_link="https://e.pcloud.link/publink/show?code=kZqCRGZXdeY3zylF4H4YyoTAczwGhEqfS7y",
        validate=ahp_validate,
        run=ahp_run,
    ),
    "csm": AlgorithmMeta(
        id="csm",
        name="Метод последовательных уступок",
        description=(
            "Метод последовательных уступок — метод многокритериальной оптимизации. "
            "На каждом шаге оптимизируется одна целевая функция при фиксированных ограничениях. "
            "Предыдущая целевая функция допускает ухудшение на заданную величину — уступку. "
            "Процесс повторяется для каждой функции, накапливая ограничения-уступки. "
            "Результатом является оптимальное решение с учётом всех критериев и уступок."
        ),
        guide_link="https://e.pcloud.link/publink/show?code=kZKCRGZORyoi01y9zFRwwiOT0nwwLuP7qGV",
        template_link="https://e.pcloud.link/publink/show?code=kZ6CRGZicE4kgj8Y4pqzPP766GlI730u1Qy",
        validate=csm_validate,
        run=csm_run,
    ),
    "tpg": AlgorithmMeta(
        id="tpg",
        name="Теория игр — Парные игры",
        description=(
            "Парные игры в нормальной форме используются для анализа стратегического взаимодействия двух игроков, "
            "когда результат зависит от выбора стратегий обеих сторон. "
            "Каждому сочетанию стратегий соответствует пара выигрышей: для первого и второго игрока. "
            "Для поиска устойчивых решений используется равновесие Нэша, которое показывает такие стратегии, "
            "при которых ни одному игроку невыгодно односторонне менять своё решение. "
            "Результатом является найденное равновесие или набор равновесий с указанием, являются ли стратегии чистыми или смешанными."
        ),
        guide_link="https://e.pcloud.link/publink/show?code=kZhOMvZw2PnpTD0TpQYgxQQ7rc2rYrRj097",
        template_link=" https://e.pcloud.link/publink/show?code=kZaEMvZuWxKK1GQyWkTuhkA3z0xQ5lQrQfy",
        validate=tpg_validate,
        run=tpg_run,
    ),
    "duu": AlgorithmMeta(
        id="duu",
        name="Теория Игр — Игры с природой",
        description=(
            "Методы принятия решений в условиях неопределённости используются для выбора оптимальной стратегии "
            "при отсутствии вероятностей состояний природы. "
            "Альтернативы оцениваются на основе платежной таблицы, отражающей возможные результаты при различных условиях. "
            "Критерий Вальда ориентирован на наихудший исход, критерий Сэвиджа минимизирует возможное сожаление, "
            "а критерий Гурвица позволяет учитывать степень оптимизма через специальный параметр. "
            "Результатом является выбранная оптимальная стратегия по каждому критерию и сравнительная оценка альтернатив."
        ),
        guide_link="https://e.pcloud.link/publink/show?code=kZeOMvZkJVGvXPFw9kWlh0chd9zKulP56Bk",
        template_link="https://e.pcloud.link/publink/show?code=kZKOMvZ9g8QpYmj0iRE0u4eYUiDc86jQB97",
        validate=duu_validate,
        run=duu_run,
    ),
    "cart": AlgorithmMeta(
        id="cart",
        name="CART — дерево решений",
        description=(
            "CART — алгоритм построения бинарного дерева решений для задачи классификации. "
            "На вход подаётся таблица с признаками, целевой переменной и колонкой 'Режим', "
            "которая разделяет строки на Тренировка, Проверка и Предсказание. "
            "Алгоритм обучается на строках 'Тренировка', проверяется на строках 'Проверка' "
            "и строит предсказания для строк 'Предсказание'. "
            "Для выбора разбиений используется критерий Джини."
        ),
        guide_link="https://e.pcloud.link/publink/show?code=kZukriZXLvVjIWn6TXJ4BjeaK9cwBB5BTmk",
        template_link="https://e.pcloud.link/publink/show?code=kZBkriZV0rMPoaWuWQlcrlPUWD8Vj7eGEJX",
        validate=cart_validate,
        run=cart_run,
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
