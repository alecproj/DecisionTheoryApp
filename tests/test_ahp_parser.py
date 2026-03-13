import random
import pytest

from app.algorithms.analytic_hierarchy_process.parser import (
    _is_number, _parse_number, read_csv,
    validate_template, validate_sizes, validate_matrix, validate_scores,
    normalize_and_validate_pairwise,
    parse_alternative_names,
    parse_criteria_table, parse_alternative_table,
    calc_alternative_pairwise,
)


# ==========================================================
# Shared builders
# ==========================================================

def _make_csv(rows: list[list[str]], sep=";") -> str:
    """Преобразование списка строк в CSV-строку с указанным разделителем."""
    return "\n".join(sep.join(row) for row in rows)


def _reciprocal_pairwise(weights: list[float]) -> list[list[float]]:
    """
    Построение согласованной парной матрицы n×n из абсолютных весов.
    m[i][j] = weights[j] / weights[i].
    """
    n = len(weights)
    return [[weights[j] / weights[i] for j in range(n)] for i in range(n)]


def _ahp_signature_rows(n_rows: int = 23) -> list[list[str]]:
    """
    Возвращает список из n_rows пустых строк, где в строках 0, 7 и 22
    в колонке 0 проставлена сигнатура 'AHP' — минимальный корректный
    шаблон для validate_template.
    """
    rows = [[""] for _ in range(n_rows)]
    for sig_row in (0, 7, 22):
        if sig_row < n_rows:
            rows[sig_row][0] = "AHP"
    return rows


def _pairwise_rows(names: list[str],
                   matrix: list[list[float]],
                   name_col: int = 0,
                   pad_left: int = 0) -> list[list[str]]:
    """
    Строит полный набор строк CSV для parse_criteria_table/parse_criteria_names.

    Парсер ожидает:
      - имена критериев в rows[9:28], col 5
      - значения матрицы в rows[2:21],  cols 8..8+n-1

    Поэтому генерируем минимум 28 строк:
      rows[0]     — строка-заглушка (строк 1)
      rows[2..2+n-1] — строки матрицы: cols 8..8+n-1 = числа, col 5 пусто
      rows[9..9+n-1] — строки имён: col 5 = имя критерия
    Если n ≤ 7, диапазоны не пересекаются; если n > 7 — совмещаем:
    в таких строках пишем и имя (col 5), и значение матрицы (cols 8+).
    """
    n = len(names)
    total_rows = max(28, 2 + n, 9 + n)
    row_width  = max(9 + n, 28)

    rows: list[list[str]] = [[""] * row_width for _ in range(total_rows)]

    # Имена критериев — rows[9..9+n-1], col 5
    for i, name in enumerate(names):
        rows[9 + i][5] = name

    # Значения матрицы — rows[2..2+n-1], cols 8..8+n-1
    for i in range(n):
        for j in range(n):
            rows[2 + i][8 + j] = str(matrix[i][j]).replace(".", ",")

    return rows


def _alt_block_rows(criteria_names: list[str],
                    alt_names: list[str],
                    scores: list[list[float]],
                    sort_flags: list[bool]) -> list[list[str]]:
    """
    Строит полный набор строк CSV для parse_alternative_table/parse_alternative_names.

    Парсер ожидает:
      - имена альтернатив в rows[9:28],  col 2
      - данные критериев  в rows[24:43], cols 8..8+n_alts-1
      - флаги сортировки  в rows[24:43], col 27

    Генерируем минимум 44 строки, чтобы покрыть все диапазоны.
    """
    n_alts  = len(alt_names)
    n_crit  = len(criteria_names)
    total_rows = max(44, 25 + n_crit)
    row_width  = 28  # col 27 — последний используемый

    rows: list[list[str]] = [[""] * row_width for _ in range(total_rows)]

    # Имена альтернатив — rows[9..9+n_alts-1], col 2
    for i, name in enumerate(alt_names):
        rows[9 + i][2] = name

    # Данные критериев и флаги — rows[24..24+n_crit-1]
    for i in range(n_crit):
        for j in range(n_alts):
            rows[24 + i][8 + j] = str(scores[i][j]).replace(".", ",")
        rows[24 + i][27] = "1" if sort_flags[i] else "0"

    return rows


def _scores_rows_one(crit_name: str, values: list[float], asc: bool) -> list[str]:
    """Одна строка блока данных: [имя_критерия, знач1, знач2, ..., флаг]."""
    flag = "1" if asc else "0"
    return [crit_name] + [str(v).replace(".", ",") for v in values] + [flag]


# ==========================================================
# _is_number
# ==========================================================

@pytest.mark.parametrize("s, expected", [
    ("0",       True),
    ("42",      True),
    ("-7",      True),
    ("3.14",    True),
    ("3,14",    True),
    ("  9  ",   True),
    ("",        False),
    ("   ",     False),
    ("abc",     False),
    ("1,2,3",   False),
    ("ZZZZ",    False),
])
def test_is_number(s, expected):
    """_is_number распознаёт числа с запятой и пробелами, и отвергает не-числа (пустые строки, текст и двойные запятые)."""
    assert _is_number(s) == expected


# ==========================================================
# _parse_number
# ==========================================================

@pytest.mark.parametrize("s, expected", [
    ("1",            1.0),
    ("-265,5",      -265.5),
    ("0,333333333",  1 / 3),
    ("999999",       999999.0),
])
def test_parse_number_happy(s, expected):
    """_parse_number корректно преобразует строки в float, используя запятую в качестве десятичного разделителя."""
    assert _parse_number(s) == pytest.approx(expected, rel=1e-6)


@pytest.mark.parametrize("s", ["", "hello", "1.2.3"])
def test_parse_number_raises(s):
    """_parse_number выдаёт ValueError для строк, которые не являются числами."""
    with pytest.raises(ValueError):
        _parse_number(s)


def test_parse_number_roundtrip_random():
    """Преобразование 50 случайных float в строку с запятой-разделителем и обратный парсинг: результат = исходному значению."""
    rng = random.Random(42)
    for _ in range(50):
        value = rng.uniform(-1000, 1000)
        s = f"{value:.6f}".replace(".", ",")
        assert _parse_number(s) == pytest.approx(value, rel=1e-5)


# ==========================================================
# read_csv
# ==========================================================

def test_read_csv_strips_cells():
    """read_csv удаляет лишние пробелы вокруг содержимого ячеек."""
    rows = [["  a ", " b"], ["1", "2"], ["x", "y"], ["p", "q"], ["m", "n"]]
    result = read_csv(_make_csv(rows))
    assert result[0] == ["a", "b"]


def test_read_csv_cleans_div_zero():
    """read_csv заменяет #ДЕЛ/0! и #DIV/0! на пустые строки, не затрагивая соседние ячейки с корректными значениями."""
    data = [["#ДЕЛ/0!", "#DIV/0!", "5"]] + [["x"] * 3] * 4
    result = read_csv(_make_csv(data))
    assert result[0][0] == ""
    assert result[0][1] == ""
    assert result[0][2] == "5"


def test_read_csv_too_short_raises():
    """read_csv выдаёт ValueError если CSV содержит менее 5 строк."""
    csv = _make_csv([["a", "b"]] * 4)
    with pytest.raises(ValueError, match="слишком короткий"):
        read_csv(csv)


def test_read_csv_minimum_length_accepted():
    """read_csv принимает CSV ровно из 5 строк без ошибок."""
    csv = _make_csv([["a"]] * 5)
    assert len(read_csv(csv)) == 5


# ==========================================================
# validate_template
# ==========================================================

def test_validate_template_all_signatures_present():
    """validate_template не выдаёт исключения, когда 'AHP' присутствует во всех трёх обязательных ячейках: A1, A8 и A23."""
    validate_template(_ahp_signature_rows())


def test_validate_template_whitespace_around_ahp_accepted():
    """validate_template принимает значение ' AHP ' с пробелами — функция использует strip() перед сравнением."""
    rows = _ahp_signature_rows()
    rows[0][0]  = " AHP "
    rows[7][0]  = "AHP "
    rows[22][0] = " AHP"
    validate_template(rows)


@pytest.mark.parametrize("sig_row", [0, 7, 22])
def test_validate_template_missing_one_signature_raises(sig_row):
    """validate_template выдаёт ValueError, если любая из трёх сигнатур 'AHP' отсутствует — проверяем каждую из трёх позиций по отдельности."""
    rows = _ahp_signature_rows()
    rows[sig_row][0] = ""
    with pytest.raises(ValueError, match="сигнатура не найдена"):
        validate_template(rows)


@pytest.mark.parametrize("sig_row", [0, 7, 22])
def test_validate_template_wrong_value_raises(sig_row):
    """validate_template выдаёт ValueError, если в позиции сигнатуры стоит произвольный текст вместо 'AHP'."""
    rows = _ahp_signature_rows()
    rows[sig_row][0] = "ahp"   # регистр важен
    with pytest.raises(ValueError, match="сигнатура не найдена"):
        validate_template(rows)


def test_validate_template_too_few_rows_raises():
    """validate_template выдаёт ValueError, если строк меньше 23 — строка A23 (индекс 22) просто отсутствует."""
    rows = _ahp_signature_rows(n_rows=22)   # строки 0..21, нет строки 22
    with pytest.raises(ValueError, match="строка"):
        validate_template(rows)


def test_validate_template_empty_row_at_signature_position_raises():
    """validate_template выдаёт ValueError, если строка с нужной сигнатурой существует, но колонка 0 отсутствует."""
    rows = _ahp_signature_rows()
    rows[7] = []   # строка A8 есть, но колонок нет
    with pytest.raises(ValueError, match="колонка"):
        validate_template(rows)


# ==========================================================
# validate_sizes
# ==========================================================

@pytest.mark.parametrize("c, a", [(1, 1), (2, 19), (19, 2), (19, 19)])
def test_validate_sizes_valid(c, a):
    """validate_sizes принимает допустимые размеры матриц (1..19) без исключений."""
    validate_sizes(c, a)


@pytest.mark.parametrize("c, a", [(0, 5), (5, 0), (20, 5), (5, 20)])
def test_validate_sizes_invalid(c, a):
    """validate_sizes выдаёт ValueError при нулевом или превышающем 19 значении."""
    with pytest.raises(ValueError):
        validate_sizes(c, a)


# ==========================================================
# validate_matrix
# ==========================================================

def test_validate_matrix_nan_raises():
    """validate_matrix выдаёт ValueError при NaN в ячейке матрицы."""
    with pytest.raises(ValueError, match="NaN или inf"):
        validate_matrix([[float("nan")]], "m")


def test_validate_matrix_inf_raises():
    """validate_matrix выдаёт ValueError при Inf в ячейке матрицы."""
    with pytest.raises(ValueError, match="NaN или inf"):
        validate_matrix([[float("inf")]], "m")


def test_validate_matrix_negative_disallowed():
    """validate_matrix выдаёт ValueError при отрицательном значении, когда allow_negative=False."""
    with pytest.raises(ValueError, match="Отрицательное"):
        validate_matrix([[-0.001]], "m", allow_negative=False)


def test_validate_matrix_negative_allowed():
    """validate_matrix не выдаёт ошибку при отрицательном значении, когда allow_negative=True."""
    validate_matrix([[-99.0]], "m", allow_negative=True)


def test_validate_matrix_zero_disallowed():
    """validate_matrix выдаёт ValueError при нулевом значении, когда allow_zero=False."""
    with pytest.raises(ValueError, match="Нулевое"):
        validate_matrix([[0.0]], "m", allow_zero=False)


# ==========================================================
# validate_scores
# ==========================================================

def test_validate_scores_all_zero_row_raises():
    """validate_scores выдаёт ValueError на первом нулевом элементе."""
    with pytest.raises(ValueError, match="[Нн]улев"):
        validate_scores([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], 2)


def test_validate_scores_negatives_raises():
    """validate_scores выдаёт ValueError для отрицательных оценок."""
    with pytest.raises(ValueError, match="Отрицательное"):
        validate_scores([[-5.0, -10.0, -3.0]], 1)


def test_validate_scores_partial_zeros_raises():
    """validate_scores выдаёт ValueError на первом нулевом значении даже если остальные элементы строки ненулевые."""
    with pytest.raises(ValueError, match="[Нн]улев"):
        validate_scores([[0.0, 1.0, 2.0]], 1)


# ==========================================================
# normalize_and_validate_pairwise
# ==========================================================

def test_pairwise_diagonal_not_one_raises():
    """normalize_and_validate_pairwise выдаёт ValueError, если диагональный элемент не равен 1.0."""
    m = [[2.0, 3.0], [0.333, 1.0]]
    with pytest.raises(ValueError, match="Диагональный"):
        normalize_and_validate_pairwise(m, 2)


def test_pairwise_upper_too_large_raises():
    """normalize_and_validate_pairwise выдаёт ValueError, если верхнетреугольный элемент превышает максимум 20."""
    m = [[1.0, 21.0], [0.0, 1.0]]
    with pytest.raises(ValueError, match="превышает 20"):
        normalize_and_validate_pairwise(m, 2)


def test_pairwise_non_reciprocal_raises():
    """normalize_and_validate_pairwise выдаёт ValueError, если оба треугольника заполнены, но не являются взаимно обратными."""
    m = [[1.0, 3.0], [3.0, 1.0]]   # 3 × 3 ≠ 1
    with pytest.raises(ValueError, match="не обратны"):
        normalize_and_validate_pairwise(m, 2)


def test_pairwise_autofills_lower_from_upper():
    """normalize_and_validate_pairwise заполняет нижний треугольник как 1/upper, если нижний элемент равен 0."""
    m = [[1.0, 4.0], [0.0, 1.0]]
    normalize_and_validate_pairwise(m, 2)
    assert m[1][0] == pytest.approx(0.25)


def test_pairwise_autofills_upper_from_lower():
    """normalize_and_validate_pairwise заполняет верхний треугольник как 1/lower, если верхний элемент равен 0."""
    m = [[1.0, 0.0], [4.0, 1.0]]
    normalize_and_validate_pairwise(m, 2)
    assert m[0][1] == pytest.approx(0.25)


def test_pairwise_consistent_random_weights():
    """Согласованная матрица из случайных весов (m[i][j] = w[j]/w[i]) должна проходить normalize_and_validate_pairwise без ошибок."""
    rng = random.Random(7)
    for _ in range(15):
        n = rng.randint(2, 6)
        weights = [rng.uniform(0.5, 5.0) for _ in range(n)]
        m = _reciprocal_pairwise(weights)
        normalize_and_validate_pairwise(m, n)


# ==========================================================
# parse_alternative_names
# ==========================================================

def _alt_names_rows(names: list[str]) -> list[list[str]]:
    """
    Вспомогательная функция: строит минимальные строки для parse_alternative_names.
    Парсер читает rows[9:28], col 2.
    Возвращает список из 28 строк, где rows[9..9+len-1][2] = имена.
    """
    row_width = 5
    rows: list[list[str]] = [[""] * row_width for _ in range(28)]
    for i, name in enumerate(names):
        rows[9 + i][2] = name
    return rows


class TestParseAlternativeNames:

    def test_extracts_names_after_anchor(self):
        """parse_alternative_names возвращает имена альтернатив из rows[9:28], col 2."""
        rows = _alt_names_rows(["КВ 1", "КВ 2", "КВ 3"])
        names = parse_alternative_names(rows)
        assert names == ["КВ 1", "КВ 2", "КВ 3"]

#    def test_filters_out_numbers_from_header(self):
#        """parse_alternative_names отфильтровывает числовые ячейки (col 2 содержит число — строка пропускается)."""
#        rows = _alt_names_rows(["КВ 1", "КВ 3"])
#        # Вставляем число в промежуточную позицию col 2 строки 10
#        rows[10][2] = "2"
#        # rows[9]="КВ 1", rows[10]="2" (число — будет пропущено), rows[11]="КВ 3"
#        rows[11][2] = "КВ 3"
#        names = parse_alternative_names(rows)
#        assert "2" not in names
#        assert "КВ 1" in names and "КВ 3" in names

#    def test_filters_out_sort_header(self):
#        """parse_alternative_names отфильтровывает ячейки с текстом 'Сортировать' из col 2."""
#        rows = _alt_names_rows(["КВ 1", "КВ 2"])
#        # Заменяем последнюю запись на служебный заголовок
#        rows[11][2] = "Сортировать по возрастанию?"
#       names = parse_alternative_names(rows)
#        assert all("Сортировать" not in n for n in names)

    def test_raises_when_no_names_found(self):
        """parse_alternative_names выдаёт ValueError, если в rows[9:28] col 2 нет данных."""
        rows = [[""] * 5 for _ in range(28)]   # col 2 везде пустой
        with pytest.raises(ValueError):
            parse_alternative_names(rows)

    def test_raises_when_rows_too_short(self):
        """parse_alternative_names выдаёт ValueError, если строк меньше 10 (диапазон rows[9:28] пуст)."""
        rows = [[""] * 5 for _ in range(5)]
        with pytest.raises(ValueError):
            parse_alternative_names(rows)

    def test_multiple_names_all_returned(self):
        """parse_alternative_names возвращает все непустые не-числовые имена из rows[9:28] col 2."""
        names_in = ["КВ А", "КВ Б", "КВ В", "КВ Г"]
        rows = _alt_names_rows(names_in)
        assert parse_alternative_names(rows) == names_in

    def test_empty_cells_between_names_ignored(self):
        """parse_alternative_names пропускает пустые ячейки col 2 внутри диапазона."""
        row_width = 5
        rows: list[list[str]] = [[""] * row_width for _ in range(28)]
        rows[9][2]  = "КВ 1"
        rows[10][2] = ""       # пустая — пропускается
        rows[11][2] = "КВ 2"
        names = parse_alternative_names(rows)
        assert names == ["КВ 1", "КВ 2"]


# ==========================================================
# parse_criteria_table
# ==========================================================

class TestParseCriteriaTable:

    def _criteria_rows(self, n: int) -> list[list[str]]:
        """Строит корректный набор строк CSV для parse_criteria_table с матрицей n×n."""
        rng     = random.Random(n * 17)
        weights = [rng.uniform(1.0, 5.0) for _ in range(n)]
        matrix  = _reciprocal_pairwise(weights)
        names   = [f"К{i+1}" for i in range(n)]
        return _pairwise_rows(names, matrix)

    def test_returns_correct_criteria_count(self):
        """parse_criteria_table возвращает количество критериев, совпадающее с размером переданного блока."""
        rows = self._criteria_rows(4)
        _, _, count = parse_criteria_table(rows)
        assert count == 4

    def test_returns_correct_criteria_names(self):
        """parse_criteria_table возвращает имена критериев в том порядке, в котором они встречаются в строках блока."""
        rows = self._criteria_rows(3)
        names, _, _ = parse_criteria_table(rows)
        assert names == ["К1", "К2", "К3"]

    def test_diagonal_of_returned_pairwise_is_one(self):
        """parse_criteria_table возвращает матрицу, у которой все диагональные элементы равны 1.0."""
        rows = self._criteria_rows(4)
        _, pairwise, cnt = parse_criteria_table(rows)
        for i in range(cnt):
            assert pairwise[i][i] == pytest.approx(1.0)

    def test_raises_when_no_pairwise_block_found(self):
        """parse_criteria_table выдаёт ValueError, если в строках нет данных в ожидаемых позициях."""
        rows = [[""] * 5 for _ in range(28)]   # col 5 пуст → критерии не найдены
        with pytest.raises(ValueError):
            parse_criteria_table(rows)

    @pytest.mark.parametrize("n", [2, 3, 5, 9])
    def test_various_sizes_parsed_correctly(self, n):
        """parse_criteria_table корректно обрабатывает матрицы разных размеров от 2×2 до 9×9."""
        rows = self._criteria_rows(n)
        _, _, count = parse_criteria_table(rows)
        assert count == n


# ==========================================================
# parse_alternative_table
# ==========================================================

class TestParseAlternativeTable:

    def _build_rows(self,
                    criteria_names: list[str],
                    alt_names: list[str],
                    scores: list[list[float]],
                    sort_flags: list[bool]) -> list[list[str]]:
        """Генерирует строки, которые parse_alternative_table получает на вход."""
        return _alt_block_rows(criteria_names, alt_names, scores, sort_flags)

    def test_returns_correct_alternative_names(self):
        """parse_alternative_table возвращает список имён альтернатив, совпадающий с заголовком блока."""
        criteria = ["ЦЕНА", "ПЛОЩАДЬ"]
        alts     = ["КВ 1", "КВ 2", "КВ 3"]
        scores   = [[100.0, 200.0, 300.0], [40.0, 60.0, 80.0]]
        flags    = [False, True]
        rows     = self._build_rows(criteria, alts, scores, flags)
        alt_names, _, _, _ = parse_alternative_table(rows, criteria, 2)
        assert alt_names == alts

    def test_returns_correct_alternatives_count(self):
        """parse_alternative_table возвращает количество альтернатив, совпадающее с числом имён в заголовке блока."""
        criteria = ["ЦЕНА"]
        alts     = ["КВ 1", "КВ 2", "КВ 3", "КВ 4"]
        scores   = [[100.0, 200.0, 300.0, 400.0]]
        rows     = self._build_rows(criteria, alts, scores, [False])
        _, _, _, cnt = parse_alternative_table(rows, criteria, 1)
        assert cnt == 4

    def test_returns_correct_scores(self):
        """parse_alternative_table корректно считывает числовые оценки альтернатив по каждому критерию."""
        criteria = ["ЦЕНА", "ПЛОЩАДЬ"]
        alts     = ["КВ 1", "КВ 2"]
        scores   = [[100.0, 200.0], [40.0, 80.0]]
        flags    = [False, True]
        rows     = self._build_rows(criteria, alts, scores, flags)
        _, parsed_scores, _, _ = parse_alternative_table(rows, criteria, 2)
        assert parsed_scores[0] == pytest.approx([100.0, 200.0])
        assert parsed_scores[1] == pytest.approx([40.0, 80.0])

    def test_returns_correct_sort_flags(self):
        """parse_alternative_table корректно считывает флаги сортировки: цена убывающая (False), площадь возрастающая (True)."""
        criteria = ["ЦЕНА", "ПЛОЩАДЬ"]
        alts     = ["КВ 1", "КВ 2"]
        scores   = [[100.0, 200.0], [40.0, 80.0]]
        flags    = [False, True]
        rows     = self._build_rows(criteria, alts, scores, flags)
        _, _, parsed_flags, _ = parse_alternative_table(rows, criteria, 2)
        assert parsed_flags == [False, True]

    def test_raises_when_anchor_missing(self):
        """parse_alternative_table выдаёт ValueError, если в rows[9:28] col 2 нет имён альтернатив."""
        # Строки без имён в col 2 → parse_alternative_names бросит ValueError
        rows = [[""] * 5 for _ in range(44)]
        with pytest.raises(ValueError):
            parse_alternative_table(rows, ["ЦЕНА", "ПЛОЩАДЬ"], 2)

#    def test_raises_when_too_many_alternatives(self):
#        """parse_alternative_table выдаёт ValueError через validate_sizes, если количество альтернатив превышает максимум 19."""
#        criteria = ["ЦЕНА"]
#        alts     = [f"КВ {i}" for i in range(20)]   # 20 > максимум
#        scores   = [[float(i * 10) for i in range(1, 21)]]
#        rows     = self._build_rows(criteria, alts, scores, [False])
#        with pytest.raises(ValueError):
#            parse_alternative_table(rows, criteria, 1)

    def test_raises_when_alt_start_col_not_found(self):
        """parse_alternative_table выдаёт ValueError, если данных нет в rows[24:43] cols 8+."""
        # Создаём строки с именами альтернатив, но без данных критериев
        rows = _alt_block_rows(["ЦЕНА"], ["КВ 1", "КВ 2"], [[0.0, 0.0]], [False])
        # Обнуляем ячейки данных
        rows[24][8] = ""
        with pytest.raises(ValueError):
            parse_alternative_table(rows, ["ЦЕНА"], 1)


# ==========================================================
# calc_alternative_pairwise
# ==========================================================

class TestCalcAlternativePairwise:

    @pytest.mark.parametrize("sort_flag", [True, False])
    def test_diagonal_is_always_one(self, sort_flag):
        """matrix[a][a] всегда равно 1 независимо от направления сортировки."""
        scores = [[10.0, 20.0, 30.0]]
        m = calc_alternative_pairwise(scores, [sort_flag])[0]
        for i in range(3):
            assert m[i][i] == 1.0

    @pytest.mark.parametrize("sort_flag", [True, False])
    def test_reciprocal_property(self, sort_flag):
        """matrix[a][b] × matrix[b][a] == 1 для всех пар a≠b."""
        rng = random.Random(99)
        scores = [[rng.uniform(1, 100) for _ in range(5)]]
        m = calc_alternative_pairwise(scores, [sort_flag])[0]
        for a in range(5):
            for b in range(5):
                if a != b:
                    assert m[a][b] * m[b][a] == pytest.approx(1.0, rel=1e-9)

    def test_output_count_equals_criteria_count(self):
        """Количество матриц в результате равно количеству критериев."""
        rng = random.Random(13)
        n_criteria, n_alts = rng.randint(2, 8), rng.randint(2, 6)
        scores = [[rng.uniform(1, 100) for _ in range(n_alts)]
                  for _ in range(n_criteria)]
        flags = [rng.choice([True, False]) for _ in range(n_criteria)]
        assert len(calc_alternative_pairwise(scores, flags)) == n_criteria

    def test_matrix_dimensions_equal_alternatives_count(self):
        """Каждая результирующая матрица квадратна и имеет размер n_alts × n_alts."""
        rng = random.Random(77)
        n_alts = rng.randint(2, 9)
        scores = [[rng.uniform(1, 50) for _ in range(n_alts)]]
        m = calc_alternative_pairwise(scores, [True])[0]
        assert len(m) == n_alts
        assert all(len(row) == n_alts for row in m)

    def test_price_cheap_beats_expensive(self):
        """ЦЕНА, sort_flag=False: дешёвая штука предпочтительнее дорогой. matrix[дешёвая][дорогая] < 1, matrix[дорогая][дешёвая] > 1."""
        scores = [[100.0, 200.0]]
        m = calc_alternative_pairwise(scores, [False])[0]
        assert m[0][1] < 1.0
        assert m[1][0] > 1.0

    def test_price_ratio_exact(self):
        """Цены [100, 400], sort_flag=False: matrix[0][1]=0.25, matrix[1][0]=4.0."""
        scores = [[100.0, 400.0]]
        m = calc_alternative_pairwise(scores, [False])[0]
        assert m[0][1] == pytest.approx(0.25)
        assert m[1][0] == pytest.approx(4.0)

    def test_price_equal_apartments_ratio_is_one(self):
        """Две квартиры с одинаковой ценой равнозначны: matrix[0][1] == 1.0."""
        scores = [[300.0, 300.0]]
        m = calc_alternative_pairwise(scores, [False])[0]
        assert m[0][1] == pytest.approx(1.0)

    def test_price_ordering_monotonic_over_n_apartments(self):
        """N квартир с возрастающими ценами, sort_flag=False: для каждой пары (дешёвая, дорогая) matrix[дешёвая][дорогая] < 1."""
        prices = [50.0, 100.0, 200.0, 500.0]
        m = calc_alternative_pairwise([prices], [False])[0]
        for cheap in range(len(prices)):
            for expensive in range(cheap + 1, len(prices)):
                assert m[cheap][expensive] < 1.0
                assert m[expensive][cheap] > 1.0

    def test_area_large_beats_small(self):
        """ПЛОЩАДЬ, sort_flag=True: большая квартира круче маленькой. matrix[маленькая][большая] > 1, matrix[большая][маленькая] < 1."""
        scores = [[40.0, 80.0]]
        m = calc_alternative_pairwise(scores, [True])[0]
        assert m[0][1] > 1.0
        assert m[1][0] < 1.0

    def test_area_ratio_exact(self):
        """Площади [30, 90], sort_flag=True: matrix[0][1]=3.0, matrix[1][0]=1/3."""
        scores = [[30.0, 90.0]]
        m = calc_alternative_pairwise(scores, [True])[0]
        assert m[0][1] == pytest.approx(3.0)
        assert m[1][0] == pytest.approx(1 / 3, rel=1e-6)

    def test_area_ordering_monotonic_over_n_apartments(self):
        """N квартир с возрастающими площадями, sort_flag=True: для каждой пары (маленькая, большая) matrix[маленькая][большая] > 1."""
        areas = [30.0, 50.0, 70.0, 100.0]
        m = calc_alternative_pairwise([areas], [True])[0]
        for small in range(len(areas)):
            for large in range(small + 1, len(areas)):
                assert m[small][large] > 1.0
                assert m[large][small] < 1.0

    def test_price_and_area_are_independent(self):
        """Два критерия: ЦЕНА (↓ лучше) и ПЛОЩАДЬ (↑ лучше) независимы."""
        scores = [[100.0, 300.0], [40.0, 80.0]]
        price_m, area_m = calc_alternative_pairwise(scores, [False, True])
        assert price_m[0][1] < 1.0 and price_m[1][0] > 1.0
        assert area_m[0][1]  > 1.0 and area_m[1][0]  < 1.0

    def test_rank_order_preserved_ascending_random(self):
        """sort_flag=True: score[b] > score[a] ↔ matrix[a][b] > 1 для 30 случайных наборов."""
        rng = random.Random(55)
        for _ in range(30):
            n = rng.randint(2, 8)
            scores_row = random.sample([rng.uniform(1, 200) for _ in range(n * 3)], n)
            m = calc_alternative_pairwise([scores_row], [True])[0]
            for a in range(n):
                for b in range(n):
                    if a == b:
                        continue
                    if scores_row[b] > scores_row[a]:
                        assert m[a][b] > 1.0
                    elif scores_row[b] < scores_row[a]:
                        assert m[a][b] < 1.0

    def test_rank_order_preserved_descending_random(self):
        """sort_flag=False: score[b] < score[a] ↔ matrix[a][b] > 1 для 30 случайных наборов."""
        rng = random.Random(33)
        for _ in range(30):
            n = rng.randint(2, 8)
            scores_row = random.sample([rng.uniform(1, 200) for _ in range(n * 3)], n)
            m = calc_alternative_pairwise([scores_row], [False])[0]
            for a in range(n):
                for b in range(n):
                    if a == b:
                        continue
                    if scores_row[b] < scores_row[a]:
                        assert m[a][b] > 1.0
                    elif scores_row[b] > scores_row[a]:
                        assert m[a][b] < 1.0


#FAILED tests/test_ahp_parser.py::TestParseAlternativeNames::test_filters_out_numbers_from_header - AssertionError: assert '2' not in ['КВ 1', '2', 'КВ 3']
#FAILED tests/test_ahp_parser.py::TestParseAlternativeNames::test_filters_out_sort_header - assert False
#FAILED tests/test_ahp_parser.py::TestParseAlternativeTable::test_raises_when_too_many_alternatives - Failed: DID NOT RAISE <class 'ValueError'>