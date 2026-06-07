# routes.py
# This file contains all API endpoints for the CheckMate system.
# We use a Flask Blueprint so the routes can be cleanly registered
# inside create_app() in app.py.


import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from database import (
    create_user,
    update_user_ids,
    get_user_by_ble_id,
    get_user_by_nfc_id,
    create_attendance_log,
    get_attendance_logs,
    get_user_by_name,
    get_all_users,
    delete_user,
    update_user_device,
    create_session, 
    get_all_sessions,
    get_active_session,
    get_db_connection
)
from uuid_generator import generate_ble_uuid
ADMIN_KEY = os.getenv("ADMIN_KEY", "default_key_change_me")
def require_admin(request):
    key = request.headers.get("Admin-Key")
    return key == ADMIN_KEY

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
    birthday = data.get("birthday")
    device_id = data.get("device_id")


    if not name or not password or not birthday:
        return jsonify({"error": "Name, password, and birthday are required"}), 400
    
    if not device_id:
        return jsonify({"error": "Device ID required"}), 400
    
    device_id = str(device_id) 
    
    # Validate birthday format
    try:
        birth_date = datetime.strptime(birthday, "%Y-%m-%d")
    except:
        return jsonify({"error": "Birthday must be YYYY-MM-DD"}), 400

    # Validate age (must be at least 10)
    today = datetime.today()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

    if age < 10:
        return jsonify({"error": "User must be at least 10 years old"}), 400

    password_hash = generate_password_hash(password)
    ble_id = generate_ble_uuid()
    nfc_id = None

    user_id = create_user(
        current_app.config["CHECKMATE_DB_PATH"],
        name,
        ble_id,
        nfc_id,
        password_hash,
        birthday,
        device_id
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

    # 5️ Determine active session
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    session = get_active_session(db_path, current_date, current_time)

    if not session:
        return jsonify({"error": "No active session right now"}), 400

    session_id = session["session_id"]

    # 6️ Determine Present or Late
    late_threshold = session["late_threshold"]

    if current_time <= late_threshold:
        status = "PRESENT"
    else:
        status = "LATE"

    # 7️ Log attendance
    create_attendance_log(db_path, user_id, session_id, method.upper(), status)

    return jsonify({
        "status": "logged",
        "user_id": user_id,
        "session_id": session_id,
        "attendance_status": status
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
    device_id = data.get("device_id")

    if not name or not password or not device_id:
        return jsonify({"error": "Name, password, and device_id are required"}), 400
    
    db_path = current_app.config["CHECKMATE_DB_PATH"]
    user = get_user_by_name(db_path, name)


    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # device lock
    if user["device_id"] is None:
        # First login ever → bind device
        update_user_device(db_path, user["user_id"], device_id)
    elif user["device_id"] != device_id:
        return jsonify({"error": "This account is already linked to another device"}), 403

    return jsonify({
        "status": "success",
        "user_id": user["user_id"],
        "name": user["name"],
        "ble_id": user["ble_id"]
    }), 200
# -----------------------------
# get all the users
# -----------------------------
@api.route("/admin/users", methods=["GET"])
def admin_get_users():
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    users = get_all_users(db_path)

    return jsonify([
        {
            "user_id": u["user_id"],
            "name": u["name"],
            "ble_id": u["ble_id"],
            "nfc_id": u["nfc_id"],
            "birthday":u["birthday"],
            "device_id": u["device_id"] 
        }
        for u in users
    ]), 200
# -----------------------------
# delete user
# -----------------------------
@api.route("/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    delete_user(db_path, user_id)

    return jsonify({"status": "deleted", "user_id": user_id}), 200

# -----------------------------
# ADMIN: CREATE SESSION
# -----------------------------
@api.route("/admin/sessions", methods=["POST"])
def admin_create_session():
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json

    session_name = data.get("session_name")
    date = data.get("date")
    day = data.get("day")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    late_threshold = data.get("late_threshold")

    # Basic validation
    if not all([session_name, date, day, start_time, end_time, late_threshold]):
        return jsonify({"error": "All fields are required"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]

    session_id = create_session(
        db_path,
        session_name,
        date,
        day,
        start_time,
        end_time,
        late_threshold
    )

    return jsonify({
        "status": "created",
        "session_id": session_id
    }), 201

# -----------------------------
# ADMIN: LIST SESSIONS
# -----------------------------
@api.route("/admin/sessions", methods=["GET"])
def admin_list_sessions():
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    sessions = get_all_sessions(db_path)

    return jsonify([
        {
            "session_id": s["session_id"],
            "session_name": s["session_name"],
            "date": s["date"],
            "day": s["day"],
            "start_time": s["start_time"],
            "end_time": s["end_time"],
            "late_threshold": s["late_threshold"],
            "created_at": s["created_at"]
        }
        for s in sessions
    ]), 200


@api.route("/admin/attendance", methods=["GET"])
def admin_attendance():
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    db_path = current_app.config["CHECKMATE_DB_PATH"]

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            a.log_id,
            a.timestamp,
            a.method,
            a.status,
            u.name AS user_name,
            s.session_name,
            s.date,
            s.start_time,
            s.end_time
        FROM attendance a
        JOIN users u ON a.user_id = u.user_id
        LEFT JOIN sessions s ON a.session_id = s.session_id
        ORDER BY a.timestamp DESC
    """)

    logs = cursor.fetchall()
    conn.close()

    return jsonify([
        {
            "log_id": row["log_id"],
            "timestamp": row["timestamp"],
            "method": row["method"],
            "status": row["status"],
            "user_name": row["user_name"],
            "session_name": row["session_name"],
            "date": row["date"],
            "start_time": row["start_time"],
            "end_time": row["end_time"]
        }
        for row in logs
    ])
