import os
from flask import Flask, send_from_directory, Response

from app.api.algorithms import bp as algorithms_bp
from app.api.runs import bp as runs_bp
from app.api.reports import bp as reports_bp


def create_app() -> Flask:
    frontend_dir = os.environ.get("FRONTEND_DIR", "/app/frontend")

    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")

    app.register_blueprint(algorithms_bp)
    app.register_blueprint(runs_bp)
    app.register_blueprint(reports_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/config.js")
    def config_js():
        mode = os.environ.get("FRONTEND_MODE", "real")
        api_base = os.environ.get("API_BASE", "")
        js = (
            "window.APP_MODE = " + repr(mode) + ";\n"
            "window.API_BASE = " + repr(api_base) + ";\n"
        )
        return Response(js, mimetype="application/javascript")

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/input.html")
    def input_page():
        return send_from_directory(frontend_dir, "input.html")

    @app.get("/report.html")
    def report_page():
        return send_from_directory(frontend_dir, "report.html")

    return app
