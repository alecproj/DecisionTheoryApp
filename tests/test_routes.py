import io
import os
import pytest

from app import create_app
from pathlib import Path

@pytest.fixture()
def client():
    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("MONGO_DB", "decision_theory_test")
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


AHP_CSV_PATH = Path(__file__).parent / "ahp_test.csv"

class TestHealth:

    def test_returns_200_json_status_ok(self, client):
        """GET /health возвращает статус 200 и JSON status=ok ."""
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json["status"] == "ok"


class TestAlgorithmsList:

    def test_returns_200(self, client):
        """GET /api/algorithms возвращает статус 200."""
        r = client.get("/api/algorithms")
        assert r.status_code == 200

    def test_response_has_algorithms_key(self, client):
        """GET /api/algorithms возвращает JSON с ключом 'algorithms' со значением списка."""
        r = client.get("/api/algorithms")
        assert "algorithms" in r.json
        assert isinstance(r.json["algorithms"], list)

    def test_contains_example_algorithm(self, client):
        """GET /api/algorithms содержит алгоритм с id='example' и 'ahp'."""
        r = client.get("/api/algorithms")
        ids = [a["id"] for a in r.json["algorithms"]]
        assert "example" in ids
        assert "ahp" in ids

    def test_algorithm_has_required_fields(self, client):
        """Каждый алгоритм в ответе содержит поля id, name, description, guide_link, template_link."""
        r = client.get("/api/algorithms")
        required = {"id", "name", "description", "guide_link", "template_link"}
        for algo in r.json["algorithms"]:
            assert required.issubset(algo.keys()), f"Алгоритм {algo} не содержит все обязательные поля"


def test_ahp_run_and_report(client):
    """Полный цикл AHP: POST /api/runs/ahp → GET /api/reports/<run_id>."""
    # --- 1. Запуск алгоритма ---
    with open(AHP_CSV_PATH, "rb") as f:
        r = client.post(
            "/api/runs/ahp",
            data={
                "report_name": "Тест AHP",
                "file": (f, "ahp_test.csv"),
            },
            content_type="multipart/form-data",
        )

    assert r.status_code == 201, f"Ожидался 201, получен {r.status_code}: {r.json}"

    body = r.json
    assert "run_id" in body
    assert body["algorithm_id"] == "ahp"
    assert body["report_name"] == "Тест AHP"

    run_id = body["run_id"]

    # --- 2. Получение отчёта ---
    rep = client.get(f"/api/reports/{run_id}")

    assert rep.status_code == 200, f"Ожидался 200, получен {rep.status_code}: {rep.json}"

    report = rep.json
    assert "markdown" in report
    assert "run_id" in report
    assert "report_name" in report

    # --- 3. Проверка содержимого отчёта ---
    md = report["markdown"]
    assert "Тест AHP" in md
    assert "ЦЕНА" in md
    assert "КВАРТИРА" in md