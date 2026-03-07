import random
import pytest

from app.algorithms.analytic_hierarchy_process.parser import ( _is_number, _parse_number, read_csv,
    validate_template, validate_sizes, validate_matrix, validate_scores,
    normalize_and_validate_pairwise, find_pairwise_matrix, parse_pairwise, parse_scores,parse_sort_asc,
    parse_alternative_names, parse_criteria_table, parse_alternative_table, calc_alternative_pairwise
)


# Shared builders

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
    Сигнатура записывается только если соответствующая строка существует.
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
    Строит сырые строки CSV, соответствующие блоку парной матрицы так, как их возвращает read_csv.
      names    — метки критериев
      matrix   — n×n числа
      name_col — столбец, где стоят метки
      pad_left — дополнительные пустые столбцы левее name_col
    """
    rows = []
    for i, name in enumerate(names):
        prefix = [""] * pad_left
        values = [str(matrix[i][j]).replace(".", ",") for j in range(len(names))]
        rows.append(prefix + [name] + values)
    return rows


def _alt_block_rows(criteria_names: list[str], alt_names: list[str], scores: list[list[float]], sort_flags: list[bool]) -> list[list[str]]:
    """
    Строит блок 'Значения критериев' так, как его ожидают parse_alternative_names, parse_scores и parse_sort_asc:

      ["...", "Значения критериев", ...]   ← строка-якорь
      ["", alt1, alt2, ..., "Сортировать по возрастанию?"]
      ["CRIT1", v1, v2, ..., "1" или "0"]
      ["CRIT2", ...]
      ...
    """
    anchor = ["", "Значения критериев"]
    header = [""] + alt_names + ["Сортировать по возрастанию?"]
    data_rows = []
    for i, crit in enumerate(criteria_names):
        flag = "1" if sort_flags[i] else "0"
        row  = [crit] + [str(v).replace(".", ",") for v in scores[i]] + [flag]
        data_rows.append(row)
    return [anchor, header] + data_rows


# is_number

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
    ("ZZZZ",  False),
])
def test_is_number(s, expected):
    """_is_number распознаёт числа с запятой и пробелами, и отвергает не-числа(пустые строки, текст и двойные запятые)."""
    assert _is_number(s) == expected


# _parse_number

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


# read_csv

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


# validate_template

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
    """validate_template выдаёт ValueError, если строка с нужной сигнатурой существует, но колонка 0 отсутствует (строка полностью пустая)."""
    rows = _ahp_signature_rows()
    rows[7] = []   # строка A8 есть, но колонок нет
    with pytest.raises(ValueError, match="колонка"):
        validate_template(rows)


# validate_sizes

@pytest.mark.parametrize("c, a", [(1, 1), (2, 19), (19, 2), (19, 19)])
def test_validate_sizes_valid(c, a):
    """validate_sizes принимает допустимые размеры матриц (1..19) без исключений."""
    validate_sizes(c, a)


@pytest.mark.parametrize("c, a", [(0, 5), (5, 0), (20, 5), (5, 20)])
def test_validate_sizes_invalid(c, a):
    """validate_sizes выдаёт ValueError при нулевом или превышающем 19 значении."""
    with pytest.raises(ValueError):
        validate_sizes(c, a)


# validate_matrix

def test_validate_matrix_nan_raises():
    """validate_matrix выдаёт ValueError при NaN в ячейке матрицы."""
    with pytest.raises(ValueError, match="NaN или inf"):
        validate_matrix([[float("nan")]], "m")


def test_validate_matrix_inf_raises():
    """validate_matrix выдаёт ValueError при Inf в ячейке матрицы."""
    with pytest.raises(ValueError, match="NaN или inf"):
        validate_matrix([[float("inf")]], "m")


def test_validate_matrix_negative_disallowed():
    """validate_matrix выдаёт ValueError при отрицательном значении, когда allow_negative=False (режим по умолчанию для парных матриц)."""
    with pytest.raises(ValueError, match="Отрицательное"):
        validate_matrix([[-0.001]], "m", allow_negative=False)


def test_validate_matrix_negative_allowed():
    """validate_matrix не выдаёт ошибку при отрицательном значении, когда allow_negative=True (используется для матриц оценок)."""
    validate_matrix([[-99.0]], "m", allow_negative=True)


def test_validate_matrix_zero_disallowed():
    """validate_matrix выдаёт ValueError при нулевом значении, когда allow_zero=False (нуль делает отношения неопределёнными)."""
    with pytest.raises(ValueError, match="Нулевое"):
        validate_matrix([[0.0]], "m", allow_zero=False)


# validate_scores

def test_validate_scores_all_zero_row_raises():
    """validate_scores выдаёт ValueError, если строка критерия полностью нулевая — такие оценки делают вычисление отношений невозможным."""
    with pytest.raises(ValueError, match="нулевая"):
        validate_scores([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], 2)


def test_validate_scores_negatives_allowed():
    """validate_scores принимает отрицательные оценки — они допустимы для критериев типа «чем меньше, тем лучше»."""
    validate_scores([[-5.0, -10.0, -3.0]], 1)


def test_validate_scores_partial_zeros_ok():
    """validate_scores принимает строку с частичными нулями, если хотя бы одно значение ненулевое."""
    validate_scores([[0.0, 1.0, 2.0]], 1)


# normalize_and_validate_pairwise

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


# find_pairwise_matrix

class TestFindPairwiseMatrix:

    def test_finds_matrix_at_top_left(self):
        """find_pairwise_matrix находит блок, начинающийся с row=0, col=0, без каких-либо отступов."""
        names  = ["К1", "К2", "К3"]
        matrix = [[1.0, 2.0, 3.0], [0.5, 1.0, 2.0], [0.333, 0.5, 1.0]]
        rows   = _pairwise_rows(names, matrix)
        start, col, max_m = find_pairwise_matrix(rows)
        assert start == 0
        assert col   == 0
        assert max_m == 3

    def test_finds_matrix_after_empty_leading_rows(self):
        """find_pairwise_matrix пропускает пустые строки сверху и находит блок, расположенный ниже."""
        names  = ["К1", "К2"]
        matrix = [[1.0, 3.0], [0.333, 1.0]]
        rows   = [["", "", ""] for _ in range(4)] + _pairwise_rows(names, matrix)
        start, col, max_m = find_pairwise_matrix(rows)
        assert start == 4
        assert max_m == 2

    def test_finds_matrix_with_offset_name_column(self):
        """find_pairwise_matrix находит блок, когда метки критериев смещены вправо на несколько пустых столбцов."""
        names  = ["К1", "К2", "К3"]
        matrix = [[1.0, 2.0, 4.0], [0.5, 1.0, 2.0], [0.25, 0.5, 1.0]]
        rows   = _pairwise_rows(names, matrix, pad_left=3)
        start, col, max_m = find_pairwise_matrix(rows)
        assert col   == 3
        assert max_m == 3

    def test_returns_none_for_all_numeric_rows(self):
        """find_pairwise_matrix возвращает (None, None, None), если все ячейки числовые — нет ни одной метки критерия для привязки."""
        rows = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        assert find_pairwise_matrix(rows) == (None, None, None)

    def test_returns_none_for_empty_rows(self):
        """find_pairwise_matrix возвращает (None, None, None) для полностью пустых строк — данных для поиска нет."""
        rows = [["", "", ""] for _ in range(5)]
        assert find_pairwise_matrix(rows) == (None, None, None)

    def test_returns_none_when_only_one_number_follows_label(self):
        """find_pairwise_matrix отвергает строку, где за меткой идёт только одно число — минимум требует двух чисел подряд."""
        rows = [["К1", "1"], ["К2", "2"], ["К3", "3"]]
        assert find_pairwise_matrix(rows) == (None, None, None)

    def test_returns_none_when_next_row_has_no_label(self):
        """find_pairwise_matrix требует, чтобы строка ниже кандидата тоже содержала метку — одиночная строка с числами не является матрицей."""
        rows = [["К1", "1", "2"], ["1", "2", "3"]]
        assert find_pairwise_matrix(rows) == (None, None, None)

    def test_max_m_is_maximum_across_all_rows(self):
        """find_pairwise_matrix устанавливает max_m равным максимальному количеству чисел по строкам блока — учитывает, что ранние строки могут быть короче поздних."""
        rows = [
            ["К1", "1",    "2",    ""],
            ["К2", "0,5",  "1",    "3"],
            ["К3", "0,25", "0,33", "1"],
        ]
        _, _, max_m = find_pairwise_matrix(rows)
        assert max_m == 3

    @pytest.mark.parametrize("n", [2, 5, 10, 19])
    def test_detects_various_matrix_sizes(self, n):
        """find_pairwise_matrix корректно определяет размер матрицы от 2×2 (минимум) до 19×19 (максимум, разрешённый AHP)."""
        rng    = random.Random(n)
        names  = [f"К{i+1}" for i in range(n)]
        matrix = [[rng.uniform(0.1, 5.0) for _ in range(n)] for _ in range(n)]
        rows   = _pairwise_rows(names, matrix)
        _, _, max_m = find_pairwise_matrix(rows)
        assert max_m == n


# parse_pairwise

class TestParsePairwise:

    def test_extracts_criteria_names_in_order(self):
        """parse_pairwise собирает метки критериев из столбца имён в том порядке, в котором они встречаются в строках."""
        rows = [["ЦЕНА", "1", "2"], ["ПЛОЩАДЬ", "0,5", "1"]]
        names, _, count = parse_pairwise(rows, pairwise_start=0, name_col=0, max_m=2)
        assert names == ["ЦЕНА", "ПЛОЩАДЬ"]
        assert count == 2

    def test_parses_float_values_with_comma_decimal(self):
        """parse_pairwise корректно читает значения матрицы, включая европейский формат с запятой в качестве десятичного разделителя."""
        rows = [["К1", "1", "3"], ["К2", "0,333333333", "1"]]
        _, matrix, _ = parse_pairwise(rows, pairwise_start=0, name_col=0, max_m=2)
        assert matrix[0][1] == pytest.approx(3.0)
        assert matrix[1][0] == pytest.approx(1 / 3, rel=1e-6)

    def test_stops_at_empty_name_cell(self):
        """parse_pairwise прекращает чтение, когда в столбце имён встречается пустая ячейка — это признак конца блока матрицы."""
        rows = [["К1", "1", "2"], ["К2", "0,5", "1"], ["", "x", "y"]]
        names, _, count = parse_pairwise(rows, pairwise_start=0, name_col=0, max_m=2)
        assert count == 2
        assert "К1" in names and "К2" in names

    def test_stops_at_numeric_name_cell(self):
        """parse_pairwise прекращает чтение, когда в столбце имён встречается число — это признак начала другого блока данных."""
        rows = [["К1", "1", "2"], ["1", "x", "y"]]
        names, _, count = parse_pairwise(rows, pairwise_start=0, name_col=0, max_m=2)
        assert count == 1
        assert names == ["К1"]

    def test_raises_on_empty_matrix_cell(self):
        """parse_pairwise выдаёт ValueError, если обязательная ячейка матрицы пуста — все позиции парного сравнения должны быть заполнены."""
        rows = [["К1", "1", ""], ["К2", "0,5", "1"]]
        with pytest.raises(ValueError, match="Пустая ячейка"):
            parse_pairwise(rows, pairwise_start=0, name_col=0, max_m=2)

    def test_raises_on_non_numeric_matrix_cell(self):
        """parse_pairwise выдаёт ValueError, если ячейка матрицы содержит текст вместо числа — все значения парных сравнений должны быть числовыми."""
        rows = [["К1", "1", "очень важно"], ["К2", "0,5", "1"]]
        with pytest.raises(ValueError, match="Некорректное значение"):
            parse_pairwise(rows, pairwise_start=0, name_col=0, max_m=2)

    def test_respects_name_col_offset(self):
        """parse_pairwise корректно читает имена и значения, когда метки критериев смещены вправо относительно нулевого столбца."""
        rows = [["", "", "К1", "1", "2"], ["", "", "К2", "0,5", "1"]]
        names, matrix, count = parse_pairwise(rows, pairwise_start=0, name_col=2, max_m=2)
        assert names == ["К1", "К2"]
        assert matrix[0][1] == pytest.approx(2.0)

    def test_pairwise_start_skips_rows_above(self):
        """parse_pairwise начинает чтение с pairwise_start и игнорирует все строки выше — они могут содержать несвязанные данные."""
        rows = [["ШУМ", "x", "y"], ["К1", "1", "4"], ["К2", "0,25", "1"]]
        names, matrix, _ = parse_pairwise(rows, pairwise_start=1, name_col=0, max_m=2)
        assert names == ["К1", "К2"]
        assert matrix[0][1] == pytest.approx(4.0)


# parse_alternative_names

class TestParseAlternativeNames:

    def test_extracts_names_after_anchor(self):
        """parse_alternative_names возвращает имена альтернатив из строки, следующей сразу за строкой с 'Значения критериев'."""
        rows = [
            ["", "Значения критериев"],
            ["", "КВ 1", "КВ 2", "КВ 3", "Сортировать по возрастанию?"],
        ]
        names = parse_alternative_names(rows)
        assert names == ["КВ 1", "КВ 2", "КВ 3"]

    def test_filters_out_numbers_from_header(self):
        """parse_alternative_names отфильтровывает числовые ячейки из строки заголовка — числа не могут быть именами альтернатив."""
        rows = [
            ["Значения критериев"],
            ["", "КВ 1", "2", "КВ 3"],
        ]
        names = parse_alternative_names(rows)
        assert "2" not in names
        assert "КВ 1" in names and "КВ 3" in names

    def test_filters_out_sortировать_header(self):
        """parse_alternative_names отфильтровывает ячейку с текстом 'Сортировать', поскольку это служебный заголовок, а не имя альтернативы."""
        rows = [
            ["Значения критериев"],
            ["", "КВ 1", "КВ 2", "Сортировать по возрастанию?"],
        ]
        names = parse_alternative_names(rows)
        assert all("Сортировать" not in n for n in names)

    def test_raises_when_anchor_missing(self):
        """parse_alternative_names выдаёт ValueError, если строка 'Значения критериев' отсутствует — без якоря невозможно найти блок альтернатив."""
        rows = [["nothing", "here"], ["no", "anchor"]]
        with pytest.raises(ValueError, match="Значения критериев"):
            parse_alternative_names(rows)

    def test_raises_when_header_row_is_empty(self):
        """parse_alternative_names выдаёт ValueError, если строка заголовка после якоря не содержит ни одного допустимого имени альтернативы."""
        rows = [
            ["Значения критериев"],
            ["", "", ""],   # пустой заголовок
        ]
        with pytest.raises(ValueError, match="спарсить"):
            parse_alternative_names(rows)

    def test_anchor_can_be_in_any_column(self):
        """parse_alternative_names находит якорь независимо от того, в каком столбце строки стоит ячейка 'Значения критериев'."""
        rows = [
            ["мусор", "", "Значения критериев", ""],
            ["", "КВ 1", "КВ 2"],
        ]
        names = parse_alternative_names(rows)
        assert names == ["КВ 1", "КВ 2"]

    def test_anchor_matched_exactly(self):
        """parse_alternative_names игнорирует строки с похожим, но не точным текстом — только точная строка 'Значения критериев' является якорем."""
        rows = [
            ["значения критериев"],   # нижний регистр — не совпадает
            ["КВ 1", "КВ 2"],
            ["Значения критериев"],   # правильный якорь
            ["КВ А", "КВ Б"],
        ]
        names = parse_alternative_names(rows)
        assert names == ["КВ А", "КВ Б"]


# parse_scores

class TestParseScores:

    def test_reads_values_correctly(self):
        """parse_scores корректно считывает числовые оценки для каждого критерия и альтернативы из ожидаемых позиций столбцов."""
        rows = [["ЦЕНА", "100", "200", "300"], ["ПЛОЩАДЬ", "40", "60", "80"]]
        scores = parse_scores(rows, ["ЦЕНА", "ПЛОЩАДЬ"],
                              data_row_start=0, criterias_cnt=2, alternatives_cnt=3)
        assert scores[0] == pytest.approx([100.0, 200.0, 300.0])
        assert scores[1] == pytest.approx([40.0, 60.0, 80.0])

    def test_parses_comma_decimal_values(self):
        """parse_scores обрабатывает европейский формат с запятой в качестве десятичного разделителя — '1,2' должно стать 1.2."""
        rows = [["ЦЕНА", "1,2", "53,5", "900,0"]]
        scores = parse_scores(rows, ["ЦЕНА"],
                              data_row_start=0, criterias_cnt=1, alternatives_cnt=3)
        assert scores[0] == pytest.approx([1.2, 53.5, 900.0])

    def test_negative_values_allowed(self):
        """parse_scores принимает отрицательные оценки — они допустимы, например, для критериев типа «долг» или «потери»."""
        rows = [["ДЕЛЬТА", "-10", "5", "-3"]]
        scores = parse_scores(rows, ["ДЕЛЬТА"],
                              data_row_start=0, criterias_cnt=1, alternatives_cnt=3)
        assert scores[0] == pytest.approx([-10.0, 5.0, -3.0])

    def test_skips_rows_before_data_row_start(self):
        """parse_scores игнорирует строки до data_row_start — строки заголовка не должны ошибочно читаться как данные."""
        rows = [["ЗАГОЛОВОК", "ALT1", "ALT2"], ["ЦЕНА", "100", "200"]]
        scores = parse_scores(rows, ["ЦЕНА"],
                              data_row_start=1, criterias_cnt=1, alternatives_cnt=2)
        assert scores[0] == pytest.approx([100.0, 200.0])

    def test_raises_when_criterion_row_missing(self):
        """parse_scores выдаёт ValueError, если критерий из criteria_names не найден ни в одной строке блока данных."""
        rows = [["ПЛОЩАДЬ", "40", "80"]]
        with pytest.raises(ValueError, match="Не все критерии найдены"):
            parse_scores(rows, ["ЦЕНА"],
                         data_row_start=0, criterias_cnt=1, alternatives_cnt=2)

    def test_raises_on_empty_cell(self):
        """parse_scores выдаёт ValueError, если ячейка оценки пуста — каждая альтернатива должна иметь значение по каждому критерию."""
        rows = [["ЦЕНА", "100", "", "300"]]
        with pytest.raises(ValueError, match="Пустая ячейка"):
            parse_scores(rows, ["ЦЕНА"],
                         data_row_start=0, criterias_cnt=1, alternatives_cnt=3)

    def test_raises_on_non_numeric_cell(self):
        """parse_scores выдаёт ValueError, если ячейка оценки содержит текст вместо числа — все оценки альтернатив должны быть числовыми."""
        rows = [["ЦЕНА", "100", "дорого", "300"]]
        with pytest.raises(ValueError, match="Некорректное значение"):
            parse_scores(rows, ["ЦЕНА"],
                         data_row_start=0, criterias_cnt=1, alternatives_cnt=3)

    def test_raises_when_row_too_short(self):
        """parse_scores выдаёт ValueError, если строка критерия содержит меньше значений, чем ожидается по количеству альтернатив."""
        rows = [["ЦЕНА", "100"]]
        with pytest.raises(ValueError):
            parse_scores(rows, ["ЦЕНА"],
                         data_row_start=0, criterias_cnt=1, alternatives_cnt=3)

    def test_criteria_matched_sequentially_by_name(self):
        """parse_scores ищет критерии последовательно в порядке criteria_names,
        сканируя строки сверху вниз — каждый следующий критерий ищется начиная
        с той строки, где был найден предыдущий. Порядок строк в CSV обязан
        совпадать с порядком в criteria_names: ЦЕНА первой, ПЛОЩАДЬ второй."""
        rows = [["ЦЕНА", "100", "200"], ["ПЛОЩАДЬ", "40", "80"]]
        scores = parse_scores(rows, ["ЦЕНА", "ПЛОЩАДЬ"],
                              data_row_start=0, criterias_cnt=2, alternatives_cnt=2)
        assert scores[0] == pytest.approx([100.0, 200.0])   # ЦЕНА
        assert scores[1] == pytest.approx([40.0, 80.0])     # ПЛОЩАДЬ


# parse_sort_asc

class TestParseSortAsc:

    def test_reads_flag_1_as_ascending(self):
        """parse_sort_asc интерпретирует флаг '1' как сортировку по возрастанию (больше = лучше), например для площади квартиры."""
        rows = [_scores_rows_one("ПЛОЩАДЬ", [40.0, 80.0], True)]
        flags = parse_sort_asc(rows, ["ПЛОЩАДЬ"], data_row_start=0,
                               criterias_cnt=1, alternatives_cnt=2)
        assert flags == [True]

    def test_reads_flag_0_as_descending(self):
        """parse_sort_asc интерпретирует флаг '0' как сортировку по убыванию (меньше = лучше), например для цены квартиры."""
        rows = [_scores_rows_one("ЦЕНА", [100.0, 200.0], False)]
        flags = parse_sort_asc(rows, ["ЦЕНА"], data_row_start=0,
                               criterias_cnt=1, alternatives_cnt=2)
        assert flags == [False]

    def test_mixed_flags_multiple_criteria(self):
        """parse_sort_asc читает независимые флаги для каждого критерия: цена по убыванию (0) и площадь по возрастанию (1) не должны мешать друг другу."""
        rows = [
            _scores_rows_one("ЦЕНА",    [100.0, 200.0], False),
            _scores_rows_one("ПЛОЩАДЬ", [40.0,  80.0],  True),
        ]
        flags = parse_sort_asc(rows, ["ЦЕНА", "ПЛОЩАДЬ"], data_row_start=0,
                               criterias_cnt=2, alternatives_cnt=2)
        assert flags == [False, True]

    #FIXED (ValueError added if flag missing)
    def test_raises_when_flag_missing(self):
        """При отсутствии столбца флага parse_sort_asc выдаёт ValueError."""
        rows = [["ЦЕНА", "100", "200"]]   # нет флага
        with pytest.raises(ValueError):
            parse_sort_asc(rows, ["ЦЕНА"], data_row_start=0,
                           criterias_cnt=1, alternatives_cnt=2)

    #FIXED (ValueError added if flag non-numeric)
    def test_raises_when_flag_is_non_numeric(self):
        """При не числовом значении флага parse_sort_asc выдаёт ValueError."""
        rows = [["ЦЕНА", "100", "200", "да"]]
        with pytest.raises(ValueError):
            parse_sort_asc(rows, ["ЦЕНА"], data_row_start=0,
                           criterias_cnt=1, alternatives_cnt=2)
            
    def test_data_row_start_skips_header(self):
        """parse_sort_asc пропускает строки до data_row_start и не читает строки заголовка как данные критериев."""
        rows = [["ШУМ", "x", "y", "0"],
                _scores_rows_one("ЦЕНА", [100.0, 200.0], False)]
        flags = parse_sort_asc(rows, ["ЦЕНА"], data_row_start=1,
                               criterias_cnt=1, alternatives_cnt=2)
        assert flags == [False]

    #FIXED (ValueError added if criterion not found)
    def test_raises_when_criterion_not_found(self):
        """parse_sort_asc выдаёт ValueError, если критерий не найден."""
        rows = [["ДРУГОЙ", "1", "2", "0"]]
        with pytest.raises(ValueError):
            parse_sort_asc(rows, ["ЦЕНА"], data_row_start=0,
                           criterias_cnt=1, alternatives_cnt=2)

    @pytest.mark.parametrize("flag_val, expected", [("0", False), ("1", True)])
    def test_both_valid_flag_values(self, flag_val, expected):
        """parse_sort_asc корректно обрабатывает оба допустимых значения флага: '0' → False (убывание), '1' → True (возрастание)."""
        rows = [["К1", "5", "10", flag_val]]
        flags = parse_sort_asc(rows, ["К1"], data_row_start=0,
                               criterias_cnt=1, alternatives_cnt=2)
        assert flags[0] == expected


# ══════════════════════════════════════════════════════════════
# parse_criteria_table  (оркестратор для блока критериев)
# ══════════════════════════════════════════════════════════════

class TestParseCriteriaTable:

    def _criteria_rows(self, n: int) -> list[list[str]]:
        """Строит корректный блок парной матрицы n×n с согласованными значениями."""
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
        """parse_criteria_table возвращает матрицу, у которой все диагональные элементы равны 1.0 (критерий равен сам себе)."""
        rows = self._criteria_rows(4)
        _, pairwise, cnt = parse_criteria_table(rows)
        for i in range(cnt):
            assert pairwise[i][i] == pytest.approx(1.0)

    def test_raises_when_no_pairwise_block_found(self):
        """parse_criteria_table выдаёт ValueError, если в строках нет распознаваемого блока парной матрицы критериев."""
        rows = [["", "", ""], ["1", "2", "3"], ["", "", ""]]
        with pytest.raises(ValueError, match="матрица критериев"):
            parse_criteria_table(rows)

    @pytest.mark.parametrize("n", [2, 3, 5, 9])
    def test_various_sizes_parsed_correctly(self, n):
        """parse_criteria_table корректно обрабатывает матрицы разных размеров от 2×2 до 9×9, возвращая правильное количество критериев."""
        rows = self._criteria_rows(n)
        _, _, count = parse_criteria_table(rows)
        assert count == n


# parse_alternative_table

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
        """parse_alternative_table выдаёт ValueError, если в строках отсутствует якорь 'Значения критериев'."""
        rows = [["ЦЕНА", "100", "200", "0"], ["ПЛОЩАДЬ", "40", "80", "1"]]
        with pytest.raises(ValueError, match="Значения критериев"):
            parse_alternative_table(rows, ["ЦЕНА", "ПЛОЩАДЬ"], 2)

    def test_raises_when_too_many_alternatives(self):
        """parse_alternative_table выдаёт ValueError через validate_sizes, если количество альтернатив превышает максимум 19."""
        criteria = ["ЦЕНА"]
        alts     = [f"КВ {i}" for i in range(20)]   # 20 > максимум
        scores   = [[float(i * 10) for i in range(1, 21)]]
        rows     = self._build_rows(criteria, alts, scores, [False])
        with pytest.raises(ValueError):
            parse_alternative_table(rows, criteria, 1)

    def test_raises_when_alt_start_col_not_found(self):
        """parse_alternative_table выдаёт ValueError, если первое имя альтернативы не найдено в строке заголовка — разметка нарушена."""
        #FIX THIS
        rows = [
            ["", "Значения критериев"],
            ["", "КВ X", "КВ Y"],      # имена не совпадают с anchor_names
            ["ЦЕНА", "100", "200", "0"],
        ]
        with pytest.raises(ValueError):
            parse_alternative_table(rows, ["UNEXISTED"], 1)


# calc_alternative_pairwise

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
        """Два критерия: ЦЕНА (↓ лучше) и ПЛОЩАДЬ (↑ лучше) независимы. По ЦЕНЕ побеждает дешёвая кв., по ПЛОЩАДИ — большая."""
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

# Вспомогательная функция (используется в TestParseSortAsc)

def _scores_rows_one(crit_name: str, values: list[float], asc: bool) -> list[str]:
    """Одна строка блока данных: [имя_критерия, знач1, знач2, ..., флаг]."""
    flag = "1" if asc else "0"
    return [crit_name] + [str(v).replace(".", ",") for v in values] + [flag]