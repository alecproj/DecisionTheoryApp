#runs.py
from flask import Blueprint, request
from app.services.run_service import create_run, upload_csv

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



@bp.post("/runs/upload/<algorithm_id>")
def upload_csv_file(algorithm_id: str):
    if "file" not in request.files:
        return {"error": "No file provided"}, 400

    file = request.files["file"]
    file_bytes = file.read()

    upload_id = upload_csv(
        algorithm_id=algorithm_id,
        filename=file.filename,
        file_bytes=file_bytes,
    )

    return {"upload_id": upload_id}, 201