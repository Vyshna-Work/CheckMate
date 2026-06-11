# ============================================================
# app.py
# PURPOSE: Creates and configures the Flask application.
#          Initialises the database, registers all API routes
#          from routes.py, and exposes the health check and
#          admin dashboard endpoints.
#
# Run standalone (debug):  python app.py
# Run via main.py (production): imported by main.py and
#          started in a background thread on port 5000.
# ============================================================

import os
from dotenv import load_dotenv

load_dotenv()  # must run before routes.py is imported so ADMIN_KEY is set

from flask import Flask, jsonify, render_template
from routes import api
from database import initialize_database


def create_app():
    app = Flask(__name__)

    # Load DB path from environment variable, fallback to test DB
    app.config["CHECKMATE_DB_PATH"] = os.getenv(
        "CHECKMATE_DB",
        "checkmate_api_test.db"
    )

    # Initialise database tables on startup
    initialize_database(app.config["CHECKMATE_DB_PATH"])

    # Register the API Blueprint
    app.register_blueprint(api)

    # Health check
    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "db_path": app.config["CHECKMATE_DB_PATH"]
        })

    # Admin dashboard
    @app.route("/admin/dashboard")
    def admin_dashboard():
        return render_template("admin_dashboard.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
