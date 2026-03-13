from dataclasses import dataclass
from typing import List

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
