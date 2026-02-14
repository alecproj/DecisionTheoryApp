import os
from pymongo import MongoClient
from pymongo.collection import Collection

_client = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        _client = MongoClient(mongo_url)
    return _client

def get_db():
    db_name = os.environ.get("MONGO_DB", "decision_theory")
    return get_client()[db_name]

def runs_col() -> Collection:
    return get_db()["runs"]

def reports_col() -> Collection:
    return get_db()["reports"]
