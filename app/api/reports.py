from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, request

from app.db.mongo import reports_col

bp = Blueprint("reports_api", __name__, url_prefix="/api")


@bp.get("/reports/<run_id>")
def report_get(run_id: str):
    try:
        oid = ObjectId(run_id)
    except InvalidId:
        return {"error": "Некорректный формат run_id", "code": "INVALID_RUN_ID"}, 400

    rep = reports_col().find_one({"run_id": oid})
    if not rep:
        return {"error": "Отчёт не найден", "code": "REPORT_NOT_FOUND"}, 404

    return {
        "run_id": run_id,
        "report_name": rep["report_name"],
        "markdown": rep["markdown"],
    }


@bp.get("/reports")
def reports_list():
    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        return {"error": "Параметр page должен быть целым числом >= 1", "code": "INVALID_PAGE"}, 400

    try:
        page_size = int(request.args.get("page_size", 50))
    except ValueError:
        return {"error": "Параметр page_size должен быть целым числом >= 1", "code": "INVALID_PAGE_SIZE"}, 400

    if page < 1:
        return {"error": "Параметр page должен быть целым числом >= 1", "code": "INVALID_PAGE"}, 400
    if page_size < 1:
        return {"error": "Параметр page_size должен быть целым числом >= 1", "code": "INVALID_PAGE_SIZE"}, 400

    col = reports_col()
    total = col.count_documents({})
    skip = (page - 1) * page_size

    docs = col.find({}, {"run_id": 1, "report_name": 1}).sort("created_at", -1).skip(skip).limit(page_size)

    items = [
        {
            "run_id": str(doc["run_id"]),
            "report_name": doc["report_name"],
        }
        for doc in docs
    ]

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }