from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

try:
    from .schema import FuzzyRelationsInput
except ImportError:
    from schema import FuzzyRelationsInput

try:
    from app.reporting.reporter import MarkdownReporter
except ImportError:
    MarkdownReporter = Any


EPS = 1e-9

def _format_number(value: float) -> str:
    """
    Форматирует число для вывода в markdown-отчет.

    Значения нечетких отношений обычно лежат в диапазоне [0; 1], поэтому
    четырех знаков после запятой достаточно для читаемого отчета. Лишние
    нули и точка в конце удаляются.
    """
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def _matrix_shape(matrix: Sequence[Sequence[float]]) -> tuple[int, int]:
    """
    Возвращает размер матрицы в виде пары (число строк, число столбцов).

    Если матрица пустая или первая строка пустая, возвращается (0, 0).
    Основная валидация выполняется в parser.py, но алгоритм дополнительно
    проверяет форму входных данных, чтобы ошибка была понятной при прямом
    вызове run(...).
    """
    rows_count = len(matrix)
    cols_count = len(matrix[0]) if rows_count else 0
    return rows_count, cols_count


def _validate_input_shapes(input_data: FuzzyRelationsInput) -> None:
    """
    Проверяет согласованность размерностей входных данных перед расчетом.

    Для композиции необходимо, чтобы:
    - R1 имела размер len(Y) x len(X);
    - R2 имела размер len(Y) x len(Z);
    - число строк Y в R1 и R2 совпадало.
    """
    y_count = len(input_data.y_names)
    x_count = len(input_data.x_names)
    z_count = len(input_data.z_names)

    r1_rows, r1_cols = _matrix_shape(input_data.r1)
    r2_rows, r2_cols = _matrix_shape(input_data.r2)

    if y_count == 0 or x_count == 0 or z_count == 0:
        raise ValueError("Множества Y, X и Z должны содержать хотя бы один элемент")

    if r1_rows != y_count or r1_cols != x_count:
        raise ValueError(
            "Размерность R1 не соответствует спискам Y и X: "
            f"ожидалось {y_count} x {x_count}, получено {r1_rows} x {r1_cols}"
        )

    if r2_rows != y_count or r2_cols != z_count:
        raise ValueError(
            "Размерность R2 не соответствует спискам Y и Z: "
            f"ожидалось {y_count} x {z_count}, получено {r2_rows} x {r2_cols}"
        )

    # Проверяем прямоугольность матриц на случай ручного создания объекта.
    for idx, row in enumerate(input_data.r1, start=1):
        if len(row) != x_count:
            raise ValueError(
                f"Строка {idx} матрицы R1 имеет длину {len(row)}, "
                f"ожидалось {x_count}"
            )

    for idx, row in enumerate(input_data.r2, start=1):
        if len(row) != z_count:
            raise ValueError(
                f"Строка {idx} матрицы R2 имеет длину {len(row)}, "
                f"ожидалось {z_count}"
            )


def compose_max_min(
    r1: Sequence[Sequence[float]],
    r2: Sequence[Sequence[float]],
) -> list[list[float]]:
    """
    Строит max-min композицию двух нечетких отношений.

    R1 задано как Y x X, R2 задано как Y x Z. Результат имеет размер X x Z:
        R(x, z) = max_y min(R1(y, x), R2(y, z)).
    """
    y_count = len(r1)
    x_count = len(r1[0])
    z_count = len(r2[0])

    result: list[list[float]] = []

    for x_idx in range(x_count):
        result_row: list[float] = []

        for z_idx in range(z_count):
            values = [
                min(float(r1[y_idx][x_idx]), float(r2[y_idx][z_idx]))
                for y_idx in range(y_count)
            ]
            result_row.append(max(values))

        result.append(result_row)

    return result


def compose_max_prod(
    r1: Sequence[Sequence[float]],
    r2: Sequence[Sequence[float]],
) -> list[list[float]]:
    """
    Строит max-prod композицию двух нечетких отношений.

    R1 задано как Y x X, R2 задано как Y x Z. Результат имеет размер X x Z:
        R(x, z) = max_y (R1(y, x) * R2(y, z)).
    """
    y_count = len(r1)
    x_count = len(r1[0])
    z_count = len(r2[0])

    result: list[list[float]] = []

    for x_idx in range(x_count):
        result_row: list[float] = []

        for z_idx in range(z_count):
            values = [
                float(r1[y_idx][x_idx]) * float(r2[y_idx][z_idx])
                for y_idx in range(y_count)
            ]
            result_row.append(max(values))

        result.append(result_row)

    return result


def _best_labels(
    values: Sequence[float],
    labels: Sequence[str],
    eps: float = EPS,
) -> tuple[list[str], float]:
    """
    Находит все элементы с максимальным значением в строке результата.

    Если максимум достигается в нескольких столбцах, возвращаются все названия,
    чтобы отчет не терял информацию о равнозначных вариантах.
    """
    max_value = max(float(value) for value in values)
    best = [
        label
        for value, label in zip(values, labels)
        if abs(float(value) - max_value) <= eps
    ]
    return best, max_value


def _format_labels(labels: Iterable[str]) -> str:
    """
    Формирует строку с названиями лучших элементов для вывода в таблицу.
    """
    return ", ".join(labels)


def _add_named_list_table(
    reporter: MarkdownReporter,
    title: str,
    prefix: str,
    names: Sequence[str],
) -> None:
    """
    Добавляет в отчет таблицу с элементами одного множества.
    """
    reporter.h2(title)
    reporter.table(
        headers=["Обозначение", "Название"],
        rows=[[f"{prefix}{idx}", name] for idx, name in enumerate(names, start=1)],
    )


def _add_relation_table(
    reporter: MarkdownReporter,
    title: str,
    row_header: str,
    row_names: Sequence[str],
    col_names: Sequence[str],
    matrix: Sequence[Sequence[float]],
) -> None:
    """
    Добавляет в отчет матрицу отношения с именованными строками и столбцами.
    """
    reporter.h2(title)

    headers = [row_header] + list(col_names)
    rows = []

    for row_name, row_values in zip(row_names, matrix):
        rows.append([row_name] + [_format_number(float(value)) for value in row_values])

    reporter.table(headers, rows)


def _build_best_rows(
    x_names: Sequence[str],
    z_names: Sequence[str],
    max_min_result: Sequence[Sequence[float]],
    max_prod_result: Sequence[Sequence[float]],
) -> list[list[str]]:
    """
    Формирует строки сравнительной таблицы лучших соответствий X -> Z.

    Для каждого элемента X определяется лучший элемент Z отдельно по методу
    max-min и отдельно по методу max-prod. Если лучшие элементы совпадают,
    в последнем столбце выводится «да», иначе — «нет».
    """
    rows: list[list[str]] = []

    for x_name, max_min_row, max_prod_row in zip(x_names, max_min_result, max_prod_result):
        max_min_best, max_min_value = _best_labels(max_min_row, z_names)
        max_prod_best, max_prod_value = _best_labels(max_prod_row, z_names)

        max_min_set = set(max_min_best)
        max_prod_set = set(max_prod_best)
        same = "да" if max_min_set == max_prod_set else "нет"

        rows.append(
            [
                x_name,
                _format_labels(max_min_best),
                _format_number(max_min_value),
                _format_labels(max_prod_best),
                _format_number(max_prod_value),
                same,
            ]
        )

    return rows


def _all_max_prod_not_greater(
    max_min_result: Sequence[Sequence[float]],
    max_prod_result: Sequence[Sequence[float]],
    eps: float = EPS,
) -> bool:
    """
    Проверяет ожидаемое свойство: max-prod не превышает max-min.

    Для чисел из диапазона [0; 1] произведение a*b не больше min(a, b),
    поэтому итоговые значения max-prod обычно меньше или равны max-min.
    """
    for row_min, row_prod in zip(max_min_result, max_prod_result):
        for value_min, value_prod in zip(row_min, row_prod):
            if float(value_prod) - float(value_min) > eps:
                return False
    return True


def run(input_data: FuzzyRelationsInput, reporter: MarkdownReporter) -> None:
    """
    Выполняет алгоритм композиции нечетких отношений и формирует отчет.

    Алгоритм принимает два отношения R1(Y, X) и R2(Y, Z), после чего строит
    результирующее отношение R(X, Z) двумя способами: max-min и max-prod.
    """
    _validate_input_shapes(input_data)

    y_names = list(input_data.y_names)
    x_names = list(input_data.x_names)
    z_names = list(input_data.z_names)
    r1 = [list(row) for row in input_data.r1]
    r2 = [list(row) for row in input_data.r2]

    max_min_result = compose_max_min(r1, r2)
    max_prod_result = compose_max_prod(r1, r2)
    best_rows = _build_best_rows(
        x_names=x_names,
        z_names=z_names,
        max_min_result=max_min_result,
        max_prod_result=max_prod_result,
    )

    reporter.h1("Композиция нечетких отношений")
    reporter.text(
        "Рассматривается задача построения результирующего нечеткого отношения "
        "между множествами X и Z через общее промежуточное множество Y. "
        "Исходное отношение R1 имеет размер Y x X, отношение R2 имеет размер Y x Z, "
        "а результат имеет размер X x Z."
    )
    reporter.text(
        "Размерность исходных данных:\n\n"
        f"- |Y| = {len(y_names)}\n"
        f"- |X| = {len(x_names)}\n"
        f"- |Z| = {len(z_names)}."
    )

    _add_named_list_table(reporter, "Множество Y", "Y", y_names)
    _add_named_list_table(reporter, "Множество X", "X", x_names)
    _add_named_list_table(reporter, "Множество Z", "Z", z_names)

    _add_relation_table(
        reporter=reporter,
        title="Исходное отношение R1(Y, X)",
        row_header="Y \\ X",
        row_names=y_names,
        col_names=x_names,
        matrix=r1,
    )

    _add_relation_table(
        reporter=reporter,
        title="Исходное отношение R2(Y, Z)",
        row_header="Y \\ Z",
        row_names=y_names,
        col_names=z_names,
        matrix=r2,
    )

    reporter.h2("Max-min композиция")
    reporter.text(
        "Для каждой пары элементов x из X и z из Z рассчитывается значение "
        "Rmax-min(x, z) = max_y min(R1(y, x), R2(y, z)). "
        "Сначала для каждого промежуточного элемента y берется минимум двух "
        "степеней принадлежности, затем выбирается максимальное значение."
    )
    _add_relation_table(
        reporter=reporter,
        title="Результирующее отношение R(X, Z) методом max-min",
        row_header="X \\ Z",
        row_names=x_names,
        col_names=z_names,
        matrix=max_min_result,
    )

    reporter.h2("Max-prod композиция")
    reporter.text(
        "Для каждой пары элементов x из X и z из Z рассчитывается значение "
        "Rmax-prod(x, z) = max_y (R1(y, x) · R2(y, z)). "
        "В отличие от max-min, здесь вместо минимума используется произведение "
        "степеней принадлежности."
    )
    _add_relation_table(
        reporter=reporter,
        title="Результирующее отношение R(X, Z) методом max-prod",
        row_header="X \\ Z",
        row_names=x_names,
        col_names=z_names,
        matrix=max_prod_result,
    )

    reporter.h2("Лучшие соответствия")
    reporter.table(
        headers=[
            "Элемент X",
            "Лучший элемент Z по max-min",
            "Значение max-min",
            "Лучший элемент Z по max-prod",
            "Значение max-prod",
            "Совпадение",
        ],
        rows=best_rows,
    )

    reporter.h2("Сравнительный анализ")

    same_count = sum(1 for row in best_rows if row[-1] == "да")
    reporter.text(
        f"Совпадение лучших соответствий по двум методам получено для "
        f"{same_count} из {len(best_rows)} элементов множества X."
    )

    if _all_max_prod_not_greater(max_min_result, max_prod_result):
        reporter.text(
            "Значения, полученные методом max-prod, не превышают значения max-min. "
            "Это ожидаемо, поскольку для степеней принадлежности из интервала [0; 1] "
            "произведение двух чисел не больше их минимума. Поэтому max-prod можно "
            "рассматривать как более строгий способ композиции."
        )
    else:
        reporter.text(
            "В рассчитанных данных обнаружены значения max-prod, превышающие max-min. "
            "Такой результат нетипичен для корректных степеней принадлежности из интервала [0; 1] "
            "и требует дополнительной проверки исходных данных."
        )

    reporter.h2("Вывод")
    reporter.text(
        "В результате построены две композиции нечетких отношений: max-min и max-prod. "
        "Матрицы результата показывают степень соответствия каждого элемента X "
        "каждому элементу Z через промежуточное множество Y. Итоговые лучшие "
        "соответствия выбираются по максимальному значению в строке результирующей матрицы."
    )
