from flask import Flask
from app.api.algorithms import bp as algorithms_bp
from app.api.runs import bp as runs_bp
from app.api.reports import bp as reports_bp

def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(algorithms_bp)
    app.register_blueprint(runs_bp)
    app.register_blueprint(reports_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
