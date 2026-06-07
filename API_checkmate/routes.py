# routes.py
# This file contains all API endpoints for the CheckMate system.
# We use a Flask Blueprint so the routes can be cleanly registered
# inside create_app() in app.py.

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from database import get_user_by_name

from database import (
    create_user,
    update_user_ids,
    get_user_by_ble_id,
    get_user_by_nfc_id,
    create_attendance_log,
    get_attendance_logs
)
from uuid_generator import generate_ble_uuid

# Create a Blueprint for all API routes
api = Blueprint("api", __name__)

# -----------------------------
# USER REGISTRATION
# -----------------------------
@api.route("/users/register", methods=["POST"])
def register_user():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"error": "Name and password are required"}), 400

    password_hash = generate_password_hash(password)
    ble_id = generate_ble_uuid()
    nfc_id = None

    user_id = create_user(
        current_app.config["CHECKMATE_DB_PATH"],
        name,
        ble_id,
        nfc_id,
        password_hash
    )

    return jsonify({
        "user_id": user_id,
        "ble_id": ble_id,
        "status": "registered"
    }), 201


# -----------------------------
# UPDATE BLE/NFC IDs (ADMIN ONLY)
# -----------------------------
@api.route("/users/update-ids", methods=["POST"])
def update_ids():
    data = request.json
    user_id = data.get("user_id")
    ble_id = data.get("ble_id")
    nfc_id = data.get("nfc_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    update_user_ids(
        current_app.config["CHECKMATE_DB_PATH"],
        user_id,
        ble_id,
        nfc_id
    )

    return jsonify({"status": "updated"}), 200


# -----------------------------
# LOG ATTENDANCE (BLE or NFC)
# -----------------------------
@api.route("/attendance/log", methods=["POST"])
def log_attendance():
    data = request.json

    method = data.get("method")
    identifier = data.get("identifier")

    # 1️ Check missing fields FIRST
    if not method or not identifier:
        return jsonify({"error": "method and identifier are required"}), 400

    # 2️ Validate method SECOND
    if method not in ["ble", "nfc"]:
        return jsonify({"error": "Invalid method"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]

    # 3️ Resolve user
    if method == "ble":
        user = get_user_by_ble_id(db_path, identifier)
    else:
        user = get_user_by_nfc_id(db_path, identifier)

    # 4️ Unknown user
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_id = user["user_id"]

    # 5️ Log attendance
    create_attendance_log(db_path, user_id, method.upper())

    return jsonify({
        "status": "logged",
        "user_id": user_id
    }), 201



# -----------------------------
# GET ATTENDANCE LOGS FOR A USER
# -----------------------------
@api.route("/attendance/user/<int:user_id>", methods=["GET"])
def get_logs(user_id):
    logs = get_attendance_logs(current_app.config["CHECKMATE_DB_PATH"], user_id)

    return jsonify({
        "user_id": user_id,
        "logs": [dict(row) for row in logs]
    }), 200

# -----------------------------
# USER SIGN IN
# -----------------------------
from werkzeug.security import check_password_hash
from database import get_user_by_name

@api.route("/auth/login", methods=["POST"])
def login_user():
    data = request.json
    name = data.get("name")
    password = data.get("password")

    if not name or not password:
        return jsonify({"error": "Name and password are required"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    user = get_user_by_name(db_path, name)

    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "status": "success",
        "user_id": user["user_id"],
        "name": user["name"],
        "ble_id": user["ble_id"]
    }), 200
