from flask import Blueprint
from app.services.run_service import get_report

bp = Blueprint("reports_api", __name__, url_prefix="/api")

@bp.get("/reports/<run_id>")
def report_get(run_id: str):
    try:
        return get_report(run_id)
    except Exception as e:
        return {"error": str(e)}, 404
