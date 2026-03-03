from flask import Blueprint, request
from app.services.run_service import create_run
from app.algorithms.registry import get_algorithm

bp = Blueprint("validate_api", __name__, url_prefix="/api")

@bp.post("/validate/<algorithm_id>")
def validate_and_run(algorithm_id: str):
    # 1) проверяем алгоритм
    try:
        get_algorithm(algorithm_id)
    except KeyError:
        return {"error": f"Алгоритм '{algorithm_id}' не найден"}, 404

    # 2) проверяем файл
    if "file" not in request.files:
        return {"error": "Файл не передан"}, 400

    file = request.files["file"]

    if file.filename == "":
        return {"error": "Файл не выбран"}, 400

    if not file.filename.endswith(".csv"):
        return {"error": "Неверный формат файла. Ожидается CSV"}, 400

    file_bytes = file.read()

    if not file_bytes:
        return {"error": "Файл пустой"}, 400

    # 3) валидация + запуск + сохранение в Mongo
    try:
        run_id = create_run(algorithm_id, file.filename, file_bytes)
    except ValueError as e:
        return {"error": str(e)}, 400

    return {"run_id": run_id}, 201