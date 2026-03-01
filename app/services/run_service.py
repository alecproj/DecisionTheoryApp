from datetime import datetime, timezone
from bson import ObjectId

from app.algorithms.registry import get_algorithm
from app.reporting.reporter import MarkdownReporter
from app.db.mongo import runs_col, reports_col

def create_run(algorithm_id: str, file_bytes: bytes) -> str:
    algo = get_algorithm(algorithm_id)

    # 1) validate (работаем с CSV bytes)
    typed_input = algo.validate(file_bytes)

    # 2) run + report
    reporter = MarkdownReporter()
    algo.run(typed_input, reporter)
    md = reporter.get_markdown()

    # 3) store
    now = datetime.now(timezone.utc)

    run_doc = {
        "algorithm_id": algorithm_id,
        "input_csv": file_bytes.decode("utf-8"),
        "created_at": now,
    }

    run_id = runs_col().insert_one(run_doc).inserted_id

    reports_col().insert_one({
        "run_id": run_id,
        "markdown": md,
        "created_at": now,
    })

    return str(run_id)

def get_report(run_id: str) -> dict:
    oid = ObjectId(run_id)
    rep = reports_col().find_one({"run_id": oid})
    if not rep:
        raise KeyError("Report not found")
    return {"run_id": run_id, "markdown": rep["markdown"]}
