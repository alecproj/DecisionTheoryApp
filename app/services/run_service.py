from datetime import datetime, timezone
from bson import ObjectId

from app.algorithms.registry import get_algorithm
from app.reporting.reporter import MarkdownReporter
from app.db.mongo import runs_col, reports_col, csv_col


def upload_csv(algorithm_id: str, filename: str, file_bytes: bytes) -> str:
    doc = {
        "algorithm_id": algorithm_id,
        "filename": filename,
        "data": file_bytes.decode("utf-8-sig"),
        "uploaded_at": datetime.now(timezone.utc),
    }
    result = csv_col(algorithm_id).insert_one(doc)
    return str(result.inserted_id)


def create_run(algorithm_id: str, filename: str, file_bytes: bytes) -> str:
    algo = get_algorithm(algorithm_id)

    # 1) сохраняем сырой CSV
    upload_csv(algorithm_id, filename, file_bytes)

    # 2) validate
    try:
        typed_input = algo.validate(file_bytes)
    except ValueError as e:
        raise ValueError(str(e))

    # 3) run + report
    try:
        reporter = MarkdownReporter()
        reporter.h1(filename)  # отчёт начинается с "# <filename>"
        algo.run(typed_input, reporter)
        md = reporter.get_markdown()
    except Exception as e:
        raise ValueError(f"Ошибка при выполнении алгоритма: {str(e)}")

    # 4) store
    now = datetime.now(timezone.utc)

    run_doc = {
        "algorithm_id": algo.id,
        "algorithm_name": algo.name,
        "algorithm_description": algo.description,
        "guide_link": algo.guide_link,
        "template_link": algo.template_link,
        "input_csv": file_bytes.decode("utf-8-sig"),
        "filename": filename,
        "created_at": now,
    }

    run_id = runs_col().insert_one(run_doc).inserted_id

    reports_col().insert_one({
        "run_id": run_id,
        "filename": filename,
        "markdown": md,
        "created_at": now,
    })

    return str(run_id)


def get_report(run_id: str) -> dict:
    oid = ObjectId(run_id)
    rep = reports_col().find_one({"run_id": oid})
    if not rep:
        raise KeyError("Отчёт не найден")
    return {"run_id": run_id, "markdown": rep["markdown"]}