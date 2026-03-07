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
class CSMInput:
    variable_cnt: int                   # количество переменных <= 5
    restriction_cnt: int                # количество ограничений <= 10
    targetfunction_cnt: int             # количество целевых функций <= 3
    concession_cnt: int                 # количество уступков (количество целевых функций - 1) <= 2
    targetfunctions: List[List[float]]  # массив целевых функций A[z1[x1, x2, ..., xk], z2[x1, x2, ..., xs],..., zn[x1, x2, ..., xu]]
    extremumtype_targetfunctions: List[String] # тип экстремума (целевая функция стремится к max/min)
    restrictions: List[List[float]]     # массив ограничений A[r1[x1, x2, ..., xk], r2[x1, x2, ..., xs],..., rk[x1, x2, ..., xu]] + учет знаков <=, =, >=
    concessions: List[float]            # массив уступков дельта1, дельта2,...,дельта(n-1)




def validator(input_data: Dict[str, Any]) -> CSMInput:
    """
    Точка входа.
    Получает CSV, полностью валидирует и возвращает CSMInput.
    """
    # --------------------------------------------------
    # 1. Проверка входа
    # --------------------------------------------------

    if "csv" not in input_data:
        raise ValueError("Обязательное поле: csv")

    csv_text = str(input_data["csv"]).strip()
    if not csv_text:
        raise ValueError("CSV пустой")

    # --------------------------------------------------
    # 2. Чтение CSV
    # --------------------------------------------------

    try:
        rows = read_csv(csv_text)
    except Exception as e:
        raise ValueError(f"Ошибка чтения CSV: {e}")

    # --------------------------------------------------
    # 3. Проверка шаблона
    # --------------------------------------------------

    try:
        validate_template(rows)
    except Exception as e:
        raise ValueError(f"Неверный шаблон CSV: {e}")

    # --------------------------------------------------
    # 4. Парсинг целевых функций
    # --------------------------------------------------

    try:
        parse_targetfunctions()
    except Exception as e:
        raise ValueError(f"Ошибка парсинга целевых функций: {e}")

    # --------------------------------------------------
    # 5. Парсинг типов экстремумов целевых функций
    # --------------------------------------------------

    try:
        parse_extremumtype_targetfunctions()
    except Exception as e:
        raise ValueError(f"Ошибка парсинга типов экстремумов целевых функций: {e}")

    # --------------------------------------------------
    # 6. Парсинг ограничений
    # --------------------------------------------------

    try:
        parse_restrictions()
    except Exception as e:
        raise ValueError(f"Ошибка парсинга ограничений: {e}")

    # --------------------------------------------------
    # 7.  Парсинг уступков
    # --------------------------------------------------

    try:
        parse_concessions()
    except Exception as e:
        raise ValueError(f"Ошибка парсинга уступков: {e}")

    # --------------------------------------------------
    # 8. Возврат модели
    # --------------------------------------------------

    return CSMInput(

        variable_cnt=variable_cnt,
        restriction_cnt=restriction_cnt,
        targetfunction_cnt=targetfunction_cnt,
        concession_cnt=concession_cnt,
        extremumtype=extremumtype,
        restrictions=restrictions,
        targetfunctions=targetfunctions,
        concessions=concessions

    )
