from typing import Any, Dict, List
from dataclasses import dataclass
from parser import (
    read_csv,
    validate_template,
    validate_sizes,
    parse_variable_cnt,
    parse_target_functions_params,
    validate_target_functions_params,
    parse_constraint_functions_params,
    validate_constraint_functions_params,
    prepare_input_data,
    validate_input_data,
)


@dataclass(frozen=True)
class CSMInput:
    variable_cnt: int                        # количество переменных <= 5
    restriction_cnt: int                     # количество ограничений <= 20
    targetfunction_cnt: int                  # количество целевых функций <= 3
    concession_cnt: int                      # количество уступков (количество целевых функций - 1) <= 2
    targetfunctions: List[List[float]]       # массив целевых функций A[z1[x1,...,xk], z2[...],...]
    extremumtype_targetfunctions: List[str]  # тип экстремума ('max' или 'min') для каждой функции
    restrictions: List[List[float]]          # массив ограничений + правая часть со знаком
    concessions: List[float]                 # массив уступков дельта1, дельта2,...,дельта(n-1)


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
    # 4. Количество переменных
    # --------------------------------------------------

    try:
        variable_cnt = parse_variable_cnt(rows)
    except Exception as e:
        raise ValueError(f"Ошибка парсинга количества переменных: {e}")

    # --------------------------------------------------
    # 5. Парсинг и валидация целевых функций
    # --------------------------------------------------

    try:
        raw_targets = parse_target_functions_params(rows)
        targetfunctions, extremumtype, concessions = validate_target_functions_params(
            raw_targets, variable_cnt
        )
    except Exception as e:
        raise ValueError(f"Ошибка парсинга целевых функций: {e}")

    # --------------------------------------------------
    # 6. Парсинг и валидация ограничений
    # --------------------------------------------------

    try:
        raw_constraints = parse_constraint_functions_params(rows)
        restrictions = validate_constraint_functions_params(raw_constraints, variable_cnt)
    except Exception as e:
        raise ValueError(f"Ошибка парсинга функций ограничения: {e}")

    # --------------------------------------------------
    # 7. Проверка размеров
    # --------------------------------------------------
    targetfunction_cnt = len(targetfunctions)
    restriction_cnt    = len(restrictions)
    concession_cnt     = len(concessions)

    try:
        validate_sizes(variable_cnt, targetfunction_cnt, restriction_cnt, concession_cnt)
    except Exception as e:
        raise ValueError(f"Ошибка проверки размеров: {e}")

    # --------------------------------------------------
    # 8. Сборка и финальная валидация
    # --------------------------------------------------

    csm_input = CSMInput(
        variable_cnt=variable_cnt,
        restriction_cnt=restriction_cnt,
        targetfunction_cnt=targetfunction_cnt,
        concession_cnt=concession_cnt,
        targetfunctions=targetfunctions,
        extremumtype_targetfunctions=extremumtype,
        restrictions=restrictions,
        concessions=concessions,
    )

    try:
        validate_input_data(csm_input)
    except Exception as e:
        raise ValueError(f"Ошибка валидации входных данных: {e}")

    # --------------------------------------------------
    # 9. Возврат результата
    # --------------------------------------------------
    return csm_input