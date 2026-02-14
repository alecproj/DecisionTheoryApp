from flask import Blueprint
from app.algorithms.registry import list_algorithms

bp = Blueprint("algorithms_api", __name__, url_prefix="/api")

@bp.get("/algorithms")
def algorithms():
    return {"algorithms": list_algorithms()}
