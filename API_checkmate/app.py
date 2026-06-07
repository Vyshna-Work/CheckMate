# app.py
# Main entry point for the CheckMate API server.
# This file creates the Flask app and registers all routes via Blueprints.

from flask import Flask, jsonify, render_template
import os
from routes import api  # import the Blueprint
from database import initialize_database

def create_app():
    app = Flask(__name__)

    # Load DB path from environment variable 
    app.config["CHECKMATE_DB_PATH"] = os.getenv(
        "CHECKMATE_DB",
        "checkmate_api_test.db"
    )

    # Initialize database
    initialize_database(app.config["CHECKMATE_DB_PATH"])

    # Register the API Blueprint
    app.register_blueprint(api)

    # Health check route
    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok",
            "db_path": app.config["CHECKMATE_DB_PATH"]
        })
    # Admin dashboard
    @app.route('/admin/dashboard')
    def admin_dashboard():
        return render_template('admin_dashboard.html')

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
