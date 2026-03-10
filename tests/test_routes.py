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

# Минимальный валидный CSV для алгоритма ahp
EXAMPLE_CSV = b"a,b\n2,3\n"
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

def _post_run(client, algorithm_id, csv_bytes=EXAMPLE_CSV,
              report_name="Тестовый отчёт", filename="data.csv"):
    """Вспомогательная функция для отправки multipart-запроса."""
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
    """POST /api/runs/example без report_name: 400 REPORT_NAME_MISSING."""
    r = _post_run(client, "example", report_name=None)
    assert r.status_code == 400
    assert r.json["code"] == "REPORT_NAME_MISSING"

def test_run_empty_report_name_returns_400(client):
    """POST /api/runs/example с пустым report_name (пробелы): 400."""
    r = _post_run(client, "example", report_name="   ")
    assert r.status_code == 400

def test_run_missing_file_returns_400(client):
    """POST /api/runs/example без файла: 400 FILE_MISSING."""
    r = _post_run(client, "example", csv_bytes=None)
    assert r.status_code == 400
    assert r.json["code"] == "FILE_MISSING"

def test_run_non_csv_extension_returns_400(client):
    """POST /api/runs/example с файлом .goida: 400 INVALID_FILE_FORMAT."""
    r = _post_run(client, "example", csv_bytes=b"a,b\n1,2", filename="data.goida")
    assert r.status_code == 400
    assert r.json["code"] == "INVALID_FILE_FORMAT"

def test_run_empty_file_returns_400(client):
    """POST /api/runs/example с пустым файлом: 400 FILE_EMPTY."""
    r = _post_run(client, "example", csv_bytes=b"")
    assert r.status_code == 400
    assert r.json["code"] == "FILE_EMPTY"

def test_run_invalid_csv_content_returns_400(client):
    """POST /api/runs/example с CSV без нужных колонок (a, b): 400 VALIDATION_ERROR."""
    r = _post_run(client, "example", csv_bytes=b"x,y\n1,2")
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

def test_run_example_success_response_shape(client):
    """POST /api/runs/example: 201 и поля algorithm_id, run_id, report_name."""
    r = _post_run(client, "example", report_name="Мой отчёт")
    assert r.status_code == 201
    assert r.json["algorithm_id"] == "example"
    assert r.json["report_name"] == "Мой отчёт"
    assert isinstance(r.json.get("run_id"), str)
    assert len(r.json["run_id"]) > 0

def test_run_produces_unique_run_ids(client):
    """Два последовательных запуска возвращают разные run_id."""
    r1 = _post_run(client, "example")
    r2 = _post_run(client, "example")
    assert r1.json["run_id"] != r2.json["run_id"]


# ══════════════════════════════════════════════════════════════
# GET /api/reports/{run_id} — ошибки (400, 404)
# ══════════════════════════════════════════════════════════════

def test_get_report_invalid_run_id_format(client):
    """GET /api/reports/not-an-objectid: 400 INVALID_RUN_ID."""
    r = client.get("/api/reports/not-an-objectid")
    assert r.status_code == 400
    assert r.json["code"] == "INVALID_RUN_ID"

    assert r.json["run_id"] == run_id
    assert r.json["report_name"] == "Имя отчёта"
    assert isinstance(r.json.get("markdown"), str)
    assert len(r.json["markdown"]) > 0

def test_get_report_example_markdown_content(client):
    """Отчёт example-алгоритма содержит раздел Result и колонку a+b."""
    run_r = _post_run(client, "example")
    r = client.get(f"/api/reports/{run_r.json['run_id']}")
    assert "Result" in r.json["markdown"]
    assert "a+b" in r.json["markdown"]


# ══════════════════════════════════════════════════════════════
# GET /api/reports — список отчётов с пагинацией
# ══════════════════════════════════════════════════════════════

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

    run_r = _post_run(client, "example", report_name="Проверка списка")
    run_id = run_r.json["run_id"]

    r = client.get("/api/reports")
    assert r.json["total"] == total_before + 1
    found = next((i for i in r.json["items"] if i["run_id"] == run_id), None)
    assert found is not None
    assert found["report_name"] == "Проверка списка"


# ══════════════════════════════════════════════════════════════
# POST /api/runs/ahp — успешный запуск (201)
# ══════════════════════════════════════════════════════════════

def test_ahp_run_success_response_shape(client):
    """POST /api/runs/ahp с валидным CSV: 201 и поля algorithm_id, run_id, report_name."""
    r = _post_ahp_run(client, report_name="Выбор квартиры")
    assert r.status_code == 201
    assert r.json["algorithm_id"] == "ahp"
    assert r.json["report_name"] == "Выбор квартиры"
    assert isinstance(r.json.get("run_id"), str)
    assert len(r.json["run_id"]) > 0


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

def test_ahp_report_contains_criteria_section(client):
    """Отчёт AHP содержит раздел с критериями."""
    run_r = _post_ahp_run(client)
    r = client.get(f"/api/reports/{run_r.json['run_id']}")
    assert r.status_code == 200
    assert "ЦЕНА" in r.json["markdown"]

def test_ahp_report_contains_alternatives(client):
    """Отчёт AHP имеет названия альтернатив из CSV."""
    run_r = _post_ahp_run(client)
    r = client.get(f"/api/reports/{run_r.json['run_id']}")
    md = r.json["markdown"]
    assert "КВАРТИРА 1" in md
    assert "КВАРТИРА 2" in md
    assert "КВАРТИРА 3" in md

def test_ahp_report_contains_consistency_section(client):
    """Отчёт AHP имеет раздел оценки согласованности и итоговые рейтинги альтернатив."""
    run_r = _post_ahp_run(client)
    r = client.get(f"/api/reports/{run_r.json['run_id']}")
    assert "CR" in r.json["markdown"]
    assert "Итоговые рейтинги" in r.json["markdown"]