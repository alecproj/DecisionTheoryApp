import os
import pytest
from app import create_app

@pytest.fixture()
def client():
    # Для локального запуска тестов без Docker Mongo:
    # можно просто пропустить тесты, требующие БД,
    # или поднять docker compose перед тестами.
    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("MONGO_DB", "decision_theory_test")

    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["status"] == "ok"

def test_list_algorithms(client):
    r = client.get("/api/algorithms")
    assert r.status_code == 200
    assert "algorithms" in r.json
    assert any(a["id"] == "example" for a in r.json["algorithms"])

def test_run_and_report(client):
    # Требует запущенного MongoDB (docker-compose up -d mongo)
    r = client.post("/api/runs", json={"algorithm_id": "example", "input": {"a": 2, "b": 3}})
    assert r.status_code == 200
    run_id = r.json["run_id"]

    rep = client.get(f"/api/reports/{run_id}")
    assert rep.status_code == 200
    assert "markdown" in rep.json
    assert "a+b" in rep.json["markdown"]
