import io
import os
import pytest
from app import create_app

@pytest.fixture()
def client():
    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("MONGO_DB", "decision_theory_test")

    app = create_app()
    app.config["TESTING"] = True

    # чистим БД перед каждым тестом
    with app.app_context():
        from app.db.mongo import get_db
        get_db().reports.drop()
        get_db().inputs.drop()

    return app.test_client()


# Минимальный валидный CSV для алгоритма csm
# 2 переменные, 2 целевые функции (max/min), 1 уступка, 2 ограничения
# Структура шаблона:
#   A1      = CSM (сигнатура)
#   F3      = 2  (variable_cnt)
#   C11:F13 = целевые функции (функция ; правая часть ; 0/1 ; уступка)
#   B17     = CSM (сигнатура)
#   C20:E39 = ограничения (функция ; знак ; правая часть)
#   F39     = CSM (сигнатура)
def _make_csm_csv(variable_cnt="2",
                  tf_rows=None,
                  constr_rows=None) -> bytes:
    """
    Собирает минимальный валидный CSM-шаблон (разделитель ;).
    tf_rows    — список строк [func, right, is_max, concession] для C11:F13 (макс 3)
    constr_rows — список строк [func, sign, right] для C20:E39 (макс 20)
    """
    if tf_rows is None:
        tf_rows = [
            ["x1+x2", "0", "1", "5"],   # Z1 = x1+x2 → max, уступка 5
            ["x1-x2", "0", "0", ""],    # Z2 = x1-x2 → min, уступка пустая (последняя)
        ]
    if constr_rows is None:
        constr_rows = [
            ["x1+x2", "<=", "10"],
            ["x1",    "<=", "6"],
        ]

    # 40 строк минимум (F39 = строка 39, индекс 38)
    rows = [[""] * 10 for _ in range(40)]

    # Сигнатуры
    rows[0][0]  = "CSM"   # A1
    rows[16][1] = "CSM"   # B17
    rows[38][5] = "CSM"   # F39

    # Количество переменных в F3 (индекс [2][5])
    rows[2][5] = variable_cnt

    # Целевые функции C11:F13 (rows[10:13], cols 2..5)
    for i, tf in enumerate(tf_rows[:3]):
        for j, val in enumerate(tf[:4]):
            rows[10 + i][2 + j] = val

    # Ограничения C20:E39 (rows[19:39], cols 2..4)
    for i, c in enumerate(constr_rows[:20]):
        for j, val in enumerate(c[:3]):
            rows[19 + i][2 + j] = val

    lines = [";".join(row) for row in rows]
    return "\n".join(lines).encode("utf-8")


CSM_CSV = _make_csm_csv()

AHP_CSV = """\
AHP;Легенда;;;;;;Сравнительная таблица важности критериев относительно друг друга;;;;;;;;;;;;;;;;;;;;
;Цвет;Тип пользовательского ввода;;;;;;ЦЕНА;РАЗМЕР;КОМНАТЫ;БЛИЗОСТЬ;КАТЕГОРИЯ;0;0;0;0;;;;;;;;;;;
;;строка;;;;;ЦЕНА;1;3;1;0,5;5;;;;;;;;;;;;;;;
;;целое число от 0 до 5;;;;;РАЗМЕР;0,333333333;1;0,25;0,14;2;;;;;;;;;;;;;;;
;;произвольное число;;;;;КОМНАТЫ;1;4;1;1;6;;;;;;;;;;;;;;;
;;0 или 1;;;;;БЛИЗОСТЬ;2;7;1;1;8;;;;;;;;;;;;;;;
;;;;;;;КАТЕГОРИЯ;0,2;0,5;0,166666667;0,125;1;;;;;;;;;;;;;;;
AHP;Названия альтернатив;;;Названия критериев;;;;;;;;;;;;;;;;;;;;;;;
;Альтернатива;Название альтернативы;;Критерий;Название критерия;;;;;;;;;;;;;;;;;;;;;;
;А1;КВАРТИРА 1;;К1;ЦЕНА;;;;;;;;;;;;;;;;;;;;;;
;А2;КВАРТИРА 2;;К2;РАЗМЕР;;;;;;;;;;;;;;;;;;;;;;
;А3;КВАРТИРА 3;;К3;КОМНАТЫ;;;;;;;;;;;;;;;;;;;;;;
;;;;K4;БЛИЗОСТЬ;;;;;;;;;;;;;;;;;;;;;;
;;;;К5;КАТЕГОРИЯ;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;;;;;;;;;;;;;;;;;;;;;;;;;;
AHP;;;;;;;Значения критериев;;;;;;;;;;;;;;;;;;;;
;;;;;;;;КВАРТИРА 1;КВАРТИРА 2;КВАРТИРА 3;0;0;0;0;0;0;;;;;;;;;;;Сортировать по возрастанию?
;;;;;;;ЦЕНА;333;100;500;;;;;;;;;;;;;;;;;0
;;;;;;;РАЗМЕР;800;1400;30;;;;;;;;;;;;;;;;;1
;;;;;;;КОМНАТЫ;22,9;25,9;10;;;;;;;;;;;;;;;;;1
;;;;;;;БЛИЗОСТЬ;31,1;70;10;;;;;;;;;;;;;;;;;1
;;;;;;;КАТЕГОРИЯ;17;10;73;;;;;;;;;;;;;;;;;1
""".encode("utf-8")


def _post_csm_run(client, csv_bytes=None,
                  report_name="Тестовый CSM отчёт", filename="csm.csv"):
    """Вспомогательная функция для отправки CSM-запроса."""
    if csv_bytes is None:
        csv_bytes = CSM_CSV
    data = {}
    if report_name is not None:
        data["report_name"] = report_name
    if csv_bytes is not None:
        data["file"] = (io.BytesIO(csv_bytes), filename)
    return client.post(
        "/api/runs/csm",
        data=data,
        content_type="multipart/form-data",
    )


def _post_ahp_run(client, csv_bytes=AHP_CSV,
                  report_name="Тестовый AHP отчёт", filename="ahp.csv"):
    """Вспомогательная функция для отправки AHP-запроса."""
    data = {}
    if report_name is not None:
        data["report_name"] = report_name
    if csv_bytes is not None:
        data["file"] = (io.BytesIO(csv_bytes), filename)
    return client.post(
        "/api/runs/ahp",
        data=data,
        content_type="multipart/form-data",
    )


def _post_run(client, algorithm_id, csv_bytes=None,
              report_name="Тестовый отчёт", filename="data.csv"):
    """Вспомогательная функция для отправки multipart-запроса."""
    if csv_bytes is None:
        csv_bytes = CSM_CSV
        filename = "data.csv"
    data = {}
    if report_name is not None:
        data["report_name"] = report_name
    if csv_bytes is not None:
        data["file"] = (io.BytesIO(csv_bytes), filename)
    return client.post(
        f"/api/runs/{algorithm_id}",
        data=data,
        content_type="multipart/form-data",
    )


def test_health(client):
    """GET /health 200 OK, status=ok."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["status"] == "ok"

# ══════════════════════════════════════════════════════════════
# GET /api/algorithms
# ══════════════════════════════════════════════════════════════

def test_list_algorithms(client):
    """GET /api/algorithms: 200 OK, поле algorithms — список."""
    r = client.get("/api/algorithms")
    assert r.status_code == 200
    assert isinstance(r.json.get("algorithms"), list)

def test_list_algorithms_each_item_has_required_fields(client):
    """Алгоритмы содержат поля id, name, description, guide_link, template_link."""
    r = client.get("/api/algorithms")
    required = {"id", "name", "description", "guide_link", "template_link"}
    for algo in r.json["algorithms"]:
        assert required <= algo.keys()

# ══════════════════════════════════════════════════════════════
# POST /api/runs/{algorithm_id} — валидационные ошибки (400)
# ══════════════════════════════════════════════════════════════

def test_run_missing_report_name_returns_400(client):
    """POST /api/runs/csm без report_name: 400 REPORT_NAME_MISSING."""
    r = _post_csm_run(client, report_name=None)
    assert r.status_code == 400
    assert r.json["code"] == "REPORT_NAME_MISSING"

def test_run_empty_report_name_returns_400(client):
    """POST /api/runs/csm с пустым report_name (пробелы): 400."""
    r = _post_csm_run(client, report_name="   ")
    assert r.status_code == 400

def test_run_missing_file_returns_400(client):
    """POST /api/runs/csm без файла: 400 FILE_MISSING."""
    r = _post_csm_run(client, csv_bytes=None, report_name="Отчёт")
    # переопределяем: не передаём файл вовсе
    data = {"report_name": "Отчёт"}
    r = client.post("/api/runs/csm", data=data, content_type="multipart/form-data")
    assert r.status_code == 400
    assert r.json["code"] == "FILE_MISSING"

def test_run_non_csv_extension_returns_400(client):
    """POST /api/runs/csm с файлом .goida: 400 INVALID_FILE_FORMAT."""
    r = _post_csm_run(client, csv_bytes=CSM_CSV, filename="data.goida")
    assert r.status_code == 400
    assert r.json["code"] == "INVALID_FILE_FORMAT"

def test_run_empty_file_returns_400(client):
    """POST /api/runs/csm с пустым файлом: 400 FILE_EMPTY."""
    r = _post_csm_run(client, csv_bytes=b"")
    assert r.status_code == 400
    assert r.json["code"] == "FILE_EMPTY"

def test_run_invalid_csv_content_returns_400(client):
    """POST /api/runs/csm с CSV без сигнатуры CSM: 400 VALIDATION_ERROR."""
    r = _post_csm_run(client, csv_bytes=b"x,y\n1,2")
    assert r.status_code == 400
    assert r.json["code"] == "VALIDATION_ERROR"

# ══════════════════════════════════════════════════════════════
# POST /api/runs/{algorithm_id} — алгоритм не найден (404)
# ══════════════════════════════════════════════════════════════

def test_run_unknown_algorithm_returns_404(client):
    """POST /api/runs/nonexistent: 404 ALGORITHM_NOT_FOUND."""
    r = _post_run(client, "nonexistent")
    assert r.status_code == 404
    assert r.json["code"] == "ALGORITHM_NOT_FOUND"


# ══════════════════════════════════════════════════════════════
# POST /api/runs/{algorithm_id} — успешный запуск (201)
# ══════════════════════════════════════════════════════════════

def test_run_csm_success_response_shape(client):
    """POST /api/runs/csm: 201 и поля algorithm_id, run_id, report_name."""
    r = _post_csm_run(client, report_name="Мой отчёт")
    assert r.status_code == 201
    assert r.json["algorithm_id"] == "csm"
    assert r.json["report_name"] == "Мой отчёт"
    assert isinstance(r.json.get("run_id"), str)
    assert len(r.json["run_id"]) > 0

def test_run_produces_unique_run_ids(client):
    """Два последовательных запуска возвращают разные run_id."""
    r1 = _post_csm_run(client)
    r2 = _post_csm_run(client)
    assert r1.json["run_id"] != r2.json["run_id"]


# ══════════════════════════════════════════════════════════════
# GET /api/reports/{run_id} — ошибки (400, 404)
# ══════════════════════════════════════════════════════════════

def test_get_report_invalid_run_id_format(client):
    """GET /api/reports/not-an-objectid: 400 INVALID_RUN_ID."""
    r = client.get("/api/reports/not-an-objectid")
    assert r.status_code == 400
    assert r.json["code"] == "INVALID_RUN_ID"

def test_get_report_nonexistent_run_id(client):
    """GET /api/reports/<валидный но несуществующий ObjectId>: 404 REPORT_NOT_FOUND."""
    r = client.get("/api/reports/000000000000000000000000")
    assert r.status_code == 404
    assert r.json["code"] == "REPORT_NOT_FOUND"


# ══════════════════════════════════════════════════════════════
# GET /api/reports/{run_id} — успешное получение отчёта (200)
# ══════════════════════════════════════════════════════════════

def test_get_report_csm(client):
    """Полный цикл csm: 200, поля run_id/report_name/markdown, содержимое МПУ и переменных."""
    run_r = _post_csm_run(client, report_name="Имя отчёта")
    assert run_r.status_code == 201
    run_id = run_r.json["run_id"]

    r = client.get(f"/api/reports/{run_id}")
    md = r.json["markdown"]

    assert r.status_code == 200
    assert r.json["run_id"] == run_id
    assert r.json["report_name"] == "Имя отчёта"
    assert isinstance(md, str)
    assert "Последовательных уступок" in md or "МПУ" in md or "уступок" in md.lower()
    assert "x1" in md


# ══════════════════════════════════════════════════════════════
# GET /api/reports — список отчётов с пагинацией
# ══════════════════════════════════════════════════════════════

def test_list_reports_response_shape(client):
    """GET /api/reports: 200 и поля page, page_size, total, items (список)."""
    r = client.get("/api/reports")
    assert r.status_code == 200
    assert isinstance(r.json.get("items"), list)
    assert {"page", "page_size", "total", "items"} <= r.json.keys()

def test_list_reports_default_pagination(client):
    """GET /api/reports без параметров: page=1 и page_size=50."""
    r = client.get("/api/reports")
    assert r.json["page"] == 1
    assert r.json["page_size"] == 50

def test_list_reports_custom_pagination(client):
    """GET /api/reports?page=2&page_size=10: корректные page и page_size."""
    r = client.get("/api/reports?page=2&page_size=10")
    assert r.json["page"] == 2
    assert r.json["page_size"] == 10

@pytest.mark.parametrize("url,expected_code", [
    ("/api/reports?page=abc",      "INVALID_PAGE"),
    ("/api/reports?page=0",        "INVALID_PAGE"),
    ("/api/reports?page_size=xyz", "INVALID_PAGE_SIZE"),
    ("/api/reports?page_size=0",   "INVALID_PAGE_SIZE"),
])
def test_list_reports_invalid_pagination_params(client, url, expected_code):
    """GET /api/reports с невалидными параметрами пагинации: 400, соответствующий code."""
    r = client.get(url)
    assert r.status_code == 400
    assert r.json["code"] == expected_code

def test_list_reports_new_run_appears_in_list(client):
    """После создания запуска отчёт появляется в списке, total увеличивается на 1, элемент содержит run_id и report_name."""
    total_before = client.get("/api/reports").json["total"]

    run_r = _post_csm_run(client, report_name="Проверка списка")
    assert run_r.status_code == 201
    run_id = run_r.json["run_id"]

    r = client.get("/api/reports")
    assert r.json["total"] == total_before + 1
    found = next((i for i in r.json["items"] if i["run_id"] == run_id), None)
    assert found is not None
    assert found["report_name"] == "Проверка списка"


# ══════════════════════════════════════════════════════════════
# POST /api/runs/ahp — успешный запуск (201)
# ══════════════════════════════════════════════════════════════

#def test_ahp_run_success_response_shape(client):
#    """POST /api/runs/ahp с валидным CSV: 201 и поля algorithm_id, run_id, report_name."""
#    r = _post_ahp_run(client, report_name="Выбор квартиры")
#    assert r.status_code == 201
#    assert r.json["algorithm_id"] == "ahp"
#    assert r.json["report_name"] == "Выбор квартиры"
#    assert isinstance(r.json.get("run_id"), str)
#    assert len(r.json["run_id"]) > 0


# ══════════════════════════════════════════════════════════════
# POST /api/runs/ahp — валидационные ошибки (400)
# ══════════════════════════════════════════════════════════════

def test_ahp_run_missing_report_name_returns_400(client):
    """POST /api/runs/ahp без report_name: 400 REPORT_NAME_MISSING."""
    r = _post_ahp_run(client, report_name=None)
    assert r.status_code == 400
    assert r.json["code"] == "REPORT_NAME_MISSING"

def test_ahp_run_missing_file_returns_400(client):
    """POST /api/runs/ahp без файла: 400 FILE_MISSING."""
    r = _post_ahp_run(client, csv_bytes=None)
    assert r.status_code == 400
    assert r.json["code"] == "FILE_MISSING"

def test_ahp_run_empty_file_returns_400(client):
    """POST /api/runs/ahp с пустым файлом: 400 FILE_EMPTY."""
    r = _post_ahp_run(client, csv_bytes=b"")
    assert r.status_code == 400
    assert r.json["code"] == "FILE_EMPTY"

def test_ahp_run_non_csv_extension_returns_400(client):
    """POST /api/runs/ahp с файлом .txt: 400 INVALID_FILE_FORMAT."""
    r = _post_ahp_run(client, csv_bytes=AHP_CSV, filename="ahp.txt")
    assert r.status_code == 400
    assert r.json["code"] == "INVALID_FILE_FORMAT"

def test_ahp_run_invalid_csv_no_ahp_signature_returns_400(client):
    """POST /api/runs/ahp с CSV без сигнатуры AHP возвращает 400 VALIDATION_ERROR."""
    r = _post_ahp_run(client, csv_bytes=b"a,b,c\n1,2,3\n")
    assert r.status_code == 400
    assert r.json["code"] == "VALIDATION_ERROR"


# ══════════════════════════════════════════════════════════════
# GET /api/reports/{run_id} — содержимое AHP отчёта
# ══════════════════════════════════════════════════════════════

#def test_ahp_report_markdown_content(client):
#    """Отчёт AHP содержит критерии, альтернативы, CR и итоговые рейтинги."""
#    run_r = _post_ahp_run(client)
#    r = client.get(f"/api/reports/{run_r.json['run_id']}")
#    md = r.json["markdown"]
#    assert r.status_code == 200
#    assert "ЦЕНА" in md
#    assert "КВАРТИРА 1" in md
#    assert "КВАРТИРА 2" in md
#    assert "КВАРТИРА 3" in md
#    assert "CR" in md
#    assert "Итоговые рейтинги" in md