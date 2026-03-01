from flask import Blueprint, request
from app.services.run_service import create_run

bp = Blueprint("runs_api", __name__, url_prefix="/api")

@bp.post("/runs")
def runs_create():
    algorithm_id = request.form.get("algorithm_id")

    if not algorithm_id:
        return {"error": "algorithm_id is required"}, 400

    if "file" not in request.files:
        return {"error": "file is required"}, 400

    file = request.files["file"]
    file_bytes = file.read()

    try:
        run_id = create_run(algorithm_id, file_bytes)
    except KeyError as e:
        return {"error": str(e)}, 404
    except ValueError as e:
        return {"error": str(e)}, 400

    return {"run_id": run_id}