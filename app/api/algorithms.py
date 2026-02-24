from flask import Blueprint, request
from app.algorithms.registry import list_algorithms, get_algorithm

bp = Blueprint("algorithms_api", __name__, url_prefix="/api")

@bp.get("/algorithms")
def algorithms():
    return {"algorithms": list_algorithms()}

@bp.post("/algorithms/<algorithm_id>/validate")
def validate_algorithm(algorithm_id: str):
    algorithm = get_algorithm(algorithm_id)

    if not algorithm:
        return {"error": "Algorithm not found"}, 404

    if "file" not in request.files:
        return {"error": "No file provided"}, 400

    file = request.files["file"]
    file_bytes = file.read()

    try:
        algorithm.validate(file_bytes)
    except ValueError as e:
        return {"error": str(e)}, 400

    return {"valid": True}