from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from .parser import (
    read_csv,
    validate_template,
    parse_criteria_table,
    parse_alternative_table,
    calc_alternative_pairwise,
)

@dataclass(frozen=True)
class AHPInput:
    criterias_cnt: int
    alternatives_cnt: int
    criteria_names: List[str]
    alternative_names: List[str]
    criteria_pairwise: List[List[float]]
    alternative_pairwise: Optional[List[List[List[float]]]] = None


def validator(input_data: Dict[str, Any]) -> AHPInput:
    """
    Точка входа.
    Получает CSV, полностью валидирует и возвращает AHPInput.
    """

    # --------------------------------------------------
    # 1. Чтение CSV
    # --------------------------------------------------

    try:
        csv_text = str(input_data["csv"]).strip()
        rows = read_csv(csv_text)
    except Exception as e:
        raise ValueError(f"Ошибка чтения CSV: {e}")

    # --------------------------------------------------
    # 2. Проверка шаблона
    # --------------------------------------------------

    try:
        validate_template(rows)
    except Exception as e:
        raise ValueError(f"Неверный шаблон CSV: {e}")

    # --------------------------------------------------
    # 3. Парсинг критериев
    # --------------------------------------------------

    try:
        criteria_names, criteria_pairwise, criterias_cnt = \
            parse_criteria_table(rows)
    except Exception as e:
        raise ValueError(f"Ошибка парсинга критериев: {e}")

    # --------------------------------------------------
    # 4. Парсинг альтернатив
    # --------------------------------------------------

    try:
        (
            alternative_names,
            scores,
            sort_flags,
            alternatives_cnt
        ) = parse_alternative_table(
            rows,
            criteria_names,
            criterias_cnt
        )
    except Exception as e:
        raise ValueError(f"Ошибка парсинга альтернатив: {e}")

    # --------------------------------------------------
    # 5. Генерация матриц альтернатив
    # --------------------------------------------------

    try:
        alternative_pairwise = calc_alternative_pairwise(
            scores,
            sort_flags
        )
    except Exception as e:
        raise ValueError(f"Ошибка генерации альтернативных матриц: {e}")

    # --------------------------------------------------
    # 6. Финальная согласованность размеров
    # --------------------------------------------------

    if criterias_cnt != len(alternative_pairwise):
        raise ValueError(
            "Количество критериев не совпадает "
            "с количеством матриц альтернатив"
        )

    # --------------------------------------------------
    # 7. Возврат модели
    # --------------------------------------------------

    return AHPInput(
        criterias_cnt=criterias_cnt,
        alternatives_cnt=alternatives_cnt,
        criteria_names=criteria_names,
        alternative_names=alternative_names,
        criteria_pairwise=criteria_pairwise,
        alternative_pairwise=alternative_pairwise
    )
