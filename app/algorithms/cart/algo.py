from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Sequence

from app.reporting.reporter import MarkdownReporter

from .schema import CARTInput


@dataclass
class Node:
    prediction: str
    samples: int
    gini: float
    class_counts: dict[str, int]

    feature_index: int | None = None
    feature_name: str | None = None
    threshold: Any | None = None
    is_numeric: bool = True
    gain: float = 0.0

    left: "Node | None" = None
    right: "Node | None" = None


def _format_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return _format_number(value)

    return str(value)


def _gini(y: Sequence[str]) -> float:
    if not y:
        return 0.0

    counts = Counter(y)
    n = len(y)

    return 1.0 - sum((count / n) ** 2 for count in counts.values())


def _majority_class(y: Sequence[str]) -> str:
    return Counter(y).most_common(1)[0][0]


def _is_numeric_column(values: Sequence[Any]) -> bool:
    return all(isinstance(value, float) for value in values)


def _candidate_thresholds(values: Sequence[Any], is_numeric: bool) -> list[Any]:
    unique = sorted(set(values))

    if len(unique) <= 1:
        return []

    if is_numeric:
        return [(unique[i] + unique[i + 1]) / 2.0 for i in range(len(unique) - 1)]

    return unique


def _split_dataset(
    X: Sequence[Sequence[Any]],
    y: Sequence[str],
    feature_index: int,
    threshold: Any,
    is_numeric: bool,
) -> tuple[list[list[Any]], list[str], list[list[Any]], list[str]]:
    left_X: list[list[Any]] = []
    left_y: list[str] = []

    right_X: list[list[Any]] = []
    right_y: list[str] = []

    for row, target in zip(X, y):
        value = row[feature_index]

        if is_numeric:
            go_left = value <= threshold
        else:
            go_left = value == threshold

        if go_left:
            left_X.append(list(row))
            left_y.append(target)
        else:
            right_X.append(list(row))
            right_y.append(target)

    return left_X, left_y, right_X, right_y


def _weighted_gini(left_y: Sequence[str], right_y: Sequence[str]) -> float:
    total = len(left_y) + len(right_y)

    return (len(left_y) / total) * _gini(left_y) + (len(right_y) / total) * _gini(right_y)


def _find_best_split(
    X: Sequence[Sequence[Any]],
    y: Sequence[str],
) -> dict[str, Any] | None:
    parent_gini = _gini(y)
    n_features = len(X[0])

    best: dict[str, Any] | None = None

    for feature_index in range(n_features):
        values = [row[feature_index] for row in X]
        is_numeric = _is_numeric_column(values)

        for threshold in _candidate_thresholds(values, is_numeric):
            left_X, left_y, right_X, right_y = _split_dataset(
                X=X,
                y=y,
                feature_index=feature_index,
                threshold=threshold,
                is_numeric=is_numeric,
            )

            if not left_y or not right_y:
                continue

            split_gini = _weighted_gini(left_y, right_y)
            gain = parent_gini - split_gini

            if best is None or gain > best["gain"]:
                best = {
                    "feature_index": feature_index,
                    "threshold": threshold,
                    "is_numeric": is_numeric,
                    "gain": gain,
                    "split_gini": split_gini,
                    "left_X": left_X,
                    "left_y": left_y,
                    "right_X": right_X,
                    "right_y": right_y,
                }

    return best


def _build_tree(
    X: Sequence[Sequence[Any]],
    y: Sequence[str],
    feature_names: Sequence[str],
    depth: int,
    max_depth: int,
    min_samples_split: int,
) -> Node:
    node = Node(
        prediction=_majority_class(y),
        samples=len(y),
        gini=_gini(y),
        class_counts=dict(Counter(y)),
    )

    if depth >= max_depth:
        return node

    if len(y) < min_samples_split:
        return node

    if len(set(y)) == 1:
        return node

    best = _find_best_split(X, y)

    if best is None or best["gain"] <= 0:
        return node

    feature_index = int(best["feature_index"])

    node.feature_index = feature_index
    node.feature_name = feature_names[feature_index]
    node.threshold = best["threshold"]
    node.is_numeric = bool(best["is_numeric"])
    node.gain = float(best["gain"])

    node.left = _build_tree(
        X=best["left_X"],
        y=best["left_y"],
        feature_names=feature_names,
        depth=depth + 1,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
    )

    node.right = _build_tree(
        X=best["right_X"],
        y=best["right_y"],
        feature_names=feature_names,
        depth=depth + 1,
        max_depth=max_depth,
        min_samples_split=min_samples_split,
    )

    return node


def _predict_one(node: Node, row: Sequence[Any]) -> str:
    current = node

    while current.feature_index is not None:
        value = row[current.feature_index]

        if current.is_numeric:
            go_left = value <= current.threshold
        else:
            go_left = value == current.threshold

        if go_left:
            if current.left is None:
                return current.prediction
            current = current.left
        else:
            if current.right is None:
                return current.prediction
            current = current.right

    return current.prediction


def _predict_many(node: Node, X: Sequence[Sequence[Any]]) -> list[str]:
    return [_predict_one(node, row) for row in X]


def _accuracy(y_true: Sequence[str], y_pred: Sequence[str]) -> float:
    if not y_true:
        return 0.0

    correct = sum(true == pred for true, pred in zip(y_true, y_pred))

    return correct / len(y_true)


def _classification_metrics(
    y_true: Sequence[str],
    y_pred: Sequence[str],
) -> list[list[str]]:
    classes = sorted(set(y_true) | set(y_pred))
    rows: list[list[str]] = []

    for cls in classes:
        true_positive = sum(
            true == cls and pred == cls
            for true, pred in zip(y_true, y_pred)
        )
        false_positive = sum(
            true != cls and pred == cls
            for true, pred in zip(y_true, y_pred)
        )
        false_negative = sum(
            true == cls and pred != cls
            for true, pred in zip(y_true, y_pred)
        )

        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive > 0
            else 0.0
        )

        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative > 0
            else 0.0
        )

        if precision + recall == 0:
            f_measure = 0.0
        else:
            f_measure = 2 * precision * recall / (precision + recall)

        rows.append(
            [
                cls,
                str(true_positive),
                str(false_positive),
                str(false_negative),
                _format_number(precision),
                _format_number(recall),
                _format_number(f_measure),
            ]
        )

    return rows


def _confusion_matrix_rows(
    y_true: Sequence[str],
    y_pred: Sequence[str],
) -> tuple[list[str], list[list[str]]]:
    classes = sorted(set(y_true) | set(y_pred))

    headers = ["Истинный класс \\ Предсказанный класс"] + classes
    rows: list[list[str]] = []

    for true_cls in classes:
        row = [true_cls]

        for pred_cls in classes:
            count = sum(
                true == true_cls and pred == pred_cls
                for true, pred in zip(y_true, y_pred)
            )
            row.append(str(count))

        rows.append(row)

    return headers, rows


def _class_counts_text(class_counts: dict[str, int]) -> str:
    parts = [f"{label}: {count}" for label, count in sorted(class_counts.items())]

    return ", ".join(parts)


def _condition_text(node: Node) -> str:
    if node.feature_name is None:
        return ""

    if node.is_numeric:
        return f"{node.feature_name} <= {_format_value(node.threshold)}"

    return f"{node.feature_name} = {_format_value(node.threshold)}"


def _render_tree(node: Node, indent: str = "") -> list[str]:
    if node.feature_index is None:
        return [
            (
                f"{indent}→ класс: {node.prediction} "
                f"(объектов: {node.samples}, "
                f"индекс Джини: {_format_number(node.gini)}, "
                f"распределение классов: [{_class_counts_text(node.class_counts)}])"
            )
        ]

    condition = _condition_text(node)

    lines = [
        (
            f"{indent}если {condition} "
            f"(улучшение: {_format_number(node.gain)}, "
            f"объектов: {node.samples}, "
            f"индекс Джини: {_format_number(node.gini)}):"
        )
    ]

    if node.left is not None:
        lines.extend(_render_tree(node.left, indent + "  "))

    lines.append(f"{indent}иначе:")

    if node.right is not None:
        lines.extend(_render_tree(node.right, indent + "  "))

    return lines


def _escape_mermaid_text(value: Any) -> str:
    text = str(value)

    replacements = {
        "\\": "\\\\",
        '"': "'",
        "\n": " ",
        "\r": " ",
        "<": "&lt;",
        ">": "&gt;",
        "{": "(",
        "}": ")",
        "[": "(",
        "]": ")",
        "|": "/",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def _mermaid_leaf_label(node: Node) -> str:
    return (
        f"Класс: {_escape_mermaid_text(node.prediction)}"
        f"<br/>объектов: {node.samples}"
        f"<br/>индекс Джини: {_format_number(node.gini)}"
        f"<br/>классы: {_escape_mermaid_text(_class_counts_text(node.class_counts))}"
    )


def _mermaid_split_label(node: Node) -> str:
    return (
        f"{_escape_mermaid_text(_condition_text(node))}"
        f"<br/>объектов: {node.samples}"
        f"<br/>индекс Джини: {_format_number(node.gini)}"
        f"<br/>улучшение: {_format_number(node.gain)}"
    )


def _render_mermaid_tree(root: Node) -> str:
    lines: list[str] = [
        "flowchart TD",

        # Общая стилизация графа под тёмный интерфейс
        "    classDef split fill:#0f2a44,stroke:#38bdf8,stroke-width:1.6px,color:#e0f2fe;",
        "    classDef leaf fill:#123524,stroke:#34d399,stroke-width:1.6px,color:#dcfce7;",
        "    classDef default font-size:13px,font-family:Arial;",

        # Стилизация линий
        "    linkStyle default stroke:#94a3b8,stroke-width:1.5px;",
    ]

    counter = 0

    def next_id() -> str:
        nonlocal counter
        counter += 1
        return f"N{counter}"

    def walk(node: Node) -> str:
        node_id = next_id()

        if node.feature_index is None:
            label = _mermaid_leaf_label(node)
            lines.append(f'    {node_id}["{label}"]:::leaf')
            return node_id

        label = _mermaid_split_label(node)
        lines.append(f'    {node_id}["{label}"]:::split')

        if node.left is not None:
            left_id = walk(node.left)
            lines.append(f'    {node_id} -- "Да" --> {left_id}')

        if node.right is not None:
            right_id = walk(node.right)
            lines.append(f'    {node_id} -- "Нет" --> {right_id}')

        return node_id

    walk(root)

    return "\n".join(lines)


def _prediction_rows(
    X: Sequence[Sequence[Any]],
    feature_names: Sequence[str],
    y_true: Sequence[str] | None,
    y_pred: Sequence[str],
) -> tuple[list[str], list[list[str]]]:
    if y_true is None:
        headers = ["№"] + list(feature_names) + ["Предсказанный класс"]
    else:
        headers = ["№"] + list(feature_names) + [
            "Истинный класс",
            "Предсказанный класс",
            "Верно",
        ]

    rows: list[list[str]] = []

    for idx, row in enumerate(X, start=1):
        base = [str(idx)] + [_format_value(value) for value in row]

        if y_true is None:
            rows.append(base + [y_pred[idx - 1]])
        else:
            true = y_true[idx - 1]
            pred = y_pred[idx - 1]
            rows.append(base + [true, pred, "да" if true == pred else "нет"])

    return headers, rows


def run(input_data: CARTInput, reporter: MarkdownReporter) -> None:
    tree = _build_tree(
        X=input_data.X_train,
        y=input_data.y_train,
        feature_names=input_data.feature_names,
        depth=0,
        max_depth=input_data.max_depth,
        min_samples_split=input_data.min_samples_split,
    )

    train_predictions = _predict_many(tree, input_data.X_train)
    test_predictions = _predict_many(tree, input_data.X_test)
    predict_predictions = _predict_many(tree, input_data.X_predict)

    train_accuracy = _accuracy(input_data.y_train, train_predictions)
    test_accuracy = _accuracy(input_data.y_test, test_predictions)

    reporter.h1("Дерево решений CART для классификации")

    reporter.text(
        "Алгоритм строит бинарное дерево решений. "
        "На каждом шаге выбирается такое разбиение данных, которое сильнее всего "
        "уменьшает неоднородность классов по индексу Джини."
    )

    reporter.h2("Сводка входных данных")
    reporter.text(
        "В этой таблице показано, какие данные были переданы алгоритму: "
        "какие признаки используются, сколько объектов отведено для обучения, "
        "сколько — для проверки, и сколько объектов нужно классифицировать без известного ответа."
    )
    reporter.table(
        headers=["Параметр", "Значение"],
        rows=[
            ["Признаки", ", ".join(input_data.feature_names)],
            ["Количество объектов для обучения", str(len(input_data.X_train))],
            ["Количество объектов для проверки", str(len(input_data.X_test))],
            ["Количество объектов для боевого предсказания", str(len(input_data.X_predict))],
            ["Классы в обучающей выборке", ", ".join(sorted(set(input_data.y_train)))],
            ["Максимальная глубина дерева", str(input_data.max_depth)],
            ["Минимум объектов для разбиения", str(input_data.min_samples_split)],
        ],
    )

    reporter.h2("Построенное дерево")
    reporter.text(
        "Ниже показано дерево решений в виде набора правил. "
        "Каждая внутренняя вершина содержит условие разбиения. "
        "Лист дерева содержит итоговый класс, который будет присвоен объекту, "
        "если объект дошёл до этого листа."
    )
    reporter.text(
        "Индекс Джини показывает неоднородность классов в вершине: "
        "чем он меньше, тем чище группа объектов. "
        "Улучшение показывает, насколько выбранное разбиение уменьшило неоднородность."
    )

    for line in _render_tree(tree):
        reporter.text(f"`{line}`")

    reporter.h2("Визуальная схема дерева")
    reporter.text(
        "Ниже приведён код схемы дерева. "
        "Его можно скопировать в редактор с поддержкой Mermaid, например Mermaid Live Editor, "
        "и увидеть дерево в виде блок-схемы."
    )
    reporter.text(
        "```mermaid\n"
        + _render_mermaid_tree(tree)
        + "\n```"
    )

    reporter.h2("Оценка качества")
    reporter.text(
        "Доля верных ответов — это часть объектов, для которых предсказанный класс "
        "совпал с истинным классом. "
        "Значение на обучающей выборке показывает, насколько дерево подогналось под данные, "
        "на которых оно строилось. "
        "Основная оценка качества — значение на проверочной выборке, потому что эти объекты "
        "не участвовали в построении дерева."
    )
    reporter.table(
        headers=["Выборка", "Доля верных ответов"],
        rows=[
            ["Обучающая", _format_number(train_accuracy)],
            ["Проверочная", _format_number(test_accuracy)],
        ],
    )

    reporter.h2("Метрики по классам на проверочной выборке")
    reporter.text(
        "Эта таблица показывает качество классификации отдельно для каждого класса. "
        "Истинно положительные — объекты данного класса, которые алгоритм правильно отнёс "
        "к этому же классу. "
        "Ложно положительные — объекты других классов, которые алгоритм ошибочно отнёс "
        "к данному классу. "
        "Ложно отрицательные — объекты данного класса, которые алгоритм ошибочно отнёс "
        "к другим классам."
    )
    reporter.text(
        "Точность показывает, какая доля объектов, предсказанных как данный класс, "
        "действительно относится к нему. "
        "Полнота показывает, какую долю объектов данного класса алгоритм смог найти. "
        "F-мера объединяет точность и полноту в одну оценку."
    )
    reporter.table(
        headers=[
            "Класс",
            "Истинно положительные",
            "Ложно положительные",
            "Ложно отрицательные",
            "Точность",
            "Полнота",
            "F-мера",
        ],
        rows=_classification_metrics(input_data.y_test, test_predictions),
    )

    reporter.h2("Матрица ошибок на проверочной выборке")
    reporter.text(
        "Матрица ошибок показывает, какие классы алгоритм путает между собой. "
        "Строки соответствуют истинным классам, столбцы — предсказанным классам. "
        "Числа на главной диагонали — верные предсказания. "
        "Остальные числа — ошибки классификации."
    )
    cm_headers, cm_rows = _confusion_matrix_rows(input_data.y_test, test_predictions)
    reporter.table(headers=cm_headers, rows=cm_rows)

    reporter.h2("Предсказания на проверочной выборке")
    reporter.text(
        "В этой таблице показано, как дерево классифицировало объекты из проверочной выборки. "
        "Для этих объектов известен истинный класс, поэтому можно сразу увидеть, "
        "где алгоритм ответил верно, а где ошибся."
    )
    test_headers, test_rows = _prediction_rows(
        X=input_data.X_test,
        feature_names=input_data.feature_names,
        y_true=input_data.y_test,
        y_pred=test_predictions,
    )
    reporter.table(headers=test_headers, rows=test_rows)

    reporter.h2("Боевые предсказания")
    reporter.text(
        "В этой таблице показаны предсказания для объектов без известного правильного ответа. "
        "Эти строки не используются ни для обучения, ни для проверки качества. "
        "Алгоритм только применяет к ним уже построенное дерево решений."
    )

    if input_data.X_predict:
        predict_headers, predict_rows = _prediction_rows(
            X=input_data.X_predict,
            feature_names=input_data.feature_names,
            y_true=None,
            y_pred=predict_predictions,
        )
        reporter.table(headers=predict_headers, rows=predict_rows)
    else:
        reporter.text("Объекты для боевого предсказания не переданы.")
