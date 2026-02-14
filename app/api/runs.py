from flask import Blueprint, request
from app.services.run_service import create_run

bp = Blueprint("runs_api", __name__, url_prefix="/api")

@bp.post("/runs")
def runs_create():
    data = request.get_json(force=True) or {}
    algorithm_id = data.get("algorithm_id")
    input_data = data.get("input", {})

    if not algorithm_id:
        return {"error": "algorithm_id is required"}, 400

    try:
        run_id = create_run(algorithm_id, input_data)
    except KeyError as e:
        return {"error": str(e)}, 404
    except ValueError as e:
        return {"error": str(e)}, 400

    return {"run_id": run_id}
