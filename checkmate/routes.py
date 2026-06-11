# routes.py
# All API endpoints for the CheckMate system.
# Uses a Flask Blueprint registered in app.py.
# Communicates with database.py for all data operations.

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from database import (
    create_user,
    update_user_ids,
    update_user_device,
    get_user_by_id,
    get_user_by_ble_id,
    get_user_by_nfc_id,
    get_user_by_name,
    get_all_users,
    delete_user,
    create_attendance_log,
    get_attendance_logs,
    get_recent_attendance,
    create_session,
    get_all_sessions,
    get_active_session,
    get_db_connection,
    get_all_settings,
    update_setting,
    delete_session
)
from uuid_generator import generate_ble_uuid

# ─────────────────────────────────────────────────────────
# ADMIN AUTH
# Simple API key check for admin-only endpoints.
# Set the ADMIN_KEY environment variable in production.
# ─────────────────────────────────────────────────────────

ADMIN_KEY = os.getenv("ADMIN_KEY", "default_key_change_me")

def require_admin(request):
    """Returns True if the request contains a valid Admin-Key header."""
    key = request.headers.get("Admin-Key")
    return key == ADMIN_KEY


# Create the Blueprint
api = Blueprint("api", __name__)


# ─────────────────────────────────────────────────────────
# USER REGISTRATION
# POST /users/register
# ─────────────────────────────────────────────────────────

@api.route("/users/register", methods=["POST"])
def register_user():
    """
    Registers a new user with name, password, birthday, and device ID.
    Generates a unique BLE UUID automatically.
    NFC ID starts as null and is assigned later when a card is linked.
    """
    data      = request.json
    name      = data.get("name")
    password  = data.get("password")
    birthday  = data.get("birthday")
    device_id = data.get("device_id")

    # Validate required fields
    if not name or not password or not birthday:
        return jsonify({"error": "Name, password, and birthday are required"}), 400

    if not device_id:
        return jsonify({"error": "Device ID is required"}), 400

    device_id = str(device_id)

    # Validate birthday format
    try:
        birth_date = datetime.strptime(birthday, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Birthday must be in YYYY-MM-DD format"}), 400

    # Validate minimum age
    today = datetime.today()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    if age < 10:
        return jsonify({"error": "User must be at least 10 years old"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]

    # Check if username already exists
    if get_user_by_name(db_path, name):
        return jsonify({"error": "Username already exists"}), 400

    # Create user
    password_hash = generate_password_hash(password)
    ble_id        = generate_ble_uuid()
    nfc_id        = None

    user_id = create_user(db_path, name, ble_id, nfc_id, password_hash, birthday, device_id)

    return jsonify({
        "user_id": user_id,
        "ble_id":  ble_id,
        "status":  "registered"
    }), 201


# ─────────────────────────────────────────────────────────
# USER LOGIN
# POST /auth/login
# ─────────────────────────────────────────────────────────

@api.route("/auth/login", methods=["POST"])
def login_user():
    """
    Authenticates a user with name, password, and device ID.
    On first login, binds the device ID to the account.
    Subsequent logins from a different device are rejected.
    """
    data      = request.json
    name      = data.get("name")
    password  = data.get("password")
    device_id = data.get("device_id")

    if not name or not password or not device_id:
        return jsonify({"error": "Name, password, and device_id are required"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    user    = get_user_by_name(db_path, name)

    # Invalid username
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    # Wrong password
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Device lock — bind on first login, reject mismatched device
    if user["device_id"] is None:
        update_user_device(db_path, user["user_id"], device_id)
    elif user["device_id"] != device_id:
        return jsonify({"error": "This account is already linked to another device"}), 403

    return jsonify({
        "status":  "success",
        "user_id": user["user_id"],
        "name":    user["name"],
        "ble_id":  user["ble_id"]
    }), 200


# ─────────────────────────────────────────────────────────
# UPDATE BLE / NFC IDs
# POST /users/update-ids
# ─────────────────────────────────────────────────────────

@api.route("/users/update-ids", methods=["POST"])
def update_ids():
    """
    Updates the BLE and/or NFC IDs for an existing user.
    Used when a user gets a new card or device.
    """
    data    = request.json
    user_id = data.get("user_id")
    ble_id  = data.get("ble_id")
    nfc_id  = data.get("nfc_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    update_user_ids(current_app.config["CHECKMATE_DB_PATH"], user_id, ble_id, nfc_id)

    return jsonify({"status": "updated"}), 200


# ─────────────────────────────────────────────────────────
# LOG ATTENDANCE (via API — mobile app or manual trigger)
# POST /attendance/log
# ─────────────────────────────────────────────────────────

@api.route("/attendance/log", methods=["POST"])
def log_attendance():
    """
    Logs an attendance entry via the API.
    Used by the mobile app or as a manual override.
    Determines PRESENT or LATE based on the active session's late_threshold.
    """
    data       = request.json
    method     = data.get("method")
    identifier = data.get("identifier")

    # Validate required fields
    if not method or not identifier:
        return jsonify({"error": "method and identifier are required"}), 400

    method = method.lower()
    if method not in ["ble", "nfc"]:
        return jsonify({"error": "method must be 'ble' or 'nfc'"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]

    # Resolve user by identifier
    if method == "ble":
        user = get_user_by_ble_id(db_path, identifier)
    else:
        user = get_user_by_nfc_id(db_path, identifier)

    if not user:
        return jsonify({"error": "User not found"}), 404

    user_id = user["user_id"]

    # Find the currently active session
    now          = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    session = get_active_session(db_path, current_date, current_time)
    if not session:
        return jsonify({"error": "No active session at this time"}), 400

    session_id = session["session_id"]

    # Determine attendance status
    status = "PRESENT" if current_time <= session["late_threshold"] else "LATE"

    # Log the attendance entry
    create_attendance_log(db_path, user_id, session_id, method.upper(), status)

    return jsonify({
        "status":            "logged",
        "user_id":           user_id,
        "session_id":        session_id,
        "attendance_status": status
    }), 201


# ─────────────────────────────────────────────────────────
# GET ATTENDANCE LOGS FOR A USER
# GET /attendance/user/<user_id>
# ─────────────────────────────────────────────────────────

@api.route("/attendance/user/<int:user_id>", methods=["GET"])
def get_logs(user_id):
    """Returns all attendance logs for a specific user, newest first."""
    logs = get_attendance_logs(current_app.config["CHECKMATE_DB_PATH"], user_id)

    return jsonify({
        "user_id": user_id,
        "logs":    [dict(row) for row in logs]
    }), 200


# ─────────────────────────────────────────────────────────
# ADMIN — LIST ALL USERS
# GET /admin/users
# ─────────────────────────────────────────────────────────

@api.route("/admin/users", methods=["GET"])
def admin_get_users():
    """Returns a list of all registered users. Admin only."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    users = get_all_users(current_app.config["CHECKMATE_DB_PATH"])

    return jsonify([
        {
            "user_id":    u["user_id"],
            "name":       u["name"],
            "ble_id":     u["ble_id"],
            "nfc_id":     u["nfc_id"],
            "birthday":   u["birthday"],
            "device_id":  u["device_id"],
            "created_at": u["created_at"],
        }
        for u in users
    ]), 200


# ─────────────────────────────────────────────────────────
# ADMIN — DELETE USER
# DELETE /admin/users/<user_id>
# ─────────────────────────────────────────────────────────

@api.route("/admin/users/<int:user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    """Deletes a user by user_id. Admin only."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    delete_user(current_app.config["CHECKMATE_DB_PATH"], user_id)

    return jsonify({"status": "deleted", "user_id": user_id}), 200


# ─────────────────────────────────────────────────────────
# ADMIN — CREATE SESSION
# POST /admin/sessions
# ─────────────────────────────────────────────────────────

@api.route("/admin/sessions", methods=["POST"])
def admin_create_session():
    """Creates a new class session. Admin only."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    data           = request.json
    session_name   = data.get("session_name")
    date           = data.get("date")
    day            = data.get("day")
    start_time     = data.get("start_time")
    end_time       = data.get("end_time")
    late_threshold = data.get("late_threshold")

    if not all([session_name, date, day, start_time, end_time, late_threshold]):
        return jsonify({"error": "All session fields are required"}), 400

    db_path    = current_app.config["CHECKMATE_DB_PATH"]
    session_id = create_session(db_path, session_name, date, day, start_time, end_time, late_threshold)

    return jsonify({"status": "created", "session_id": session_id}), 201


# ─────────────────────────────────────────────────────────
# ADMIN — LIST ALL SESSIONS
# GET /admin/sessions
# ─────────────────────────────────────────────────────────

@api.route("/admin/sessions", methods=["GET"])
def admin_list_sessions():
    """Returns all class sessions. Admin only."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    sessions = get_all_sessions(current_app.config["CHECKMATE_DB_PATH"])

    return jsonify([
        {
            "session_id":    s["session_id"],
            "session_name":  s["session_name"],
            "date":          s["date"],
            "day":           s["day"],
            "start_time":    s["start_time"],
            "end_time":      s["end_time"],
            "late_threshold": s["late_threshold"],
            "created_at":    s["created_at"]
        }
        for s in sessions
    ]), 200


# ─────────────────────────────────────────────────────────
# ADMIN — SESSION REPORT
# GET /admin/sessions/<session_id>/report
# Returns every registered user with their attendance status
# for the given session. Users with no record show as PENDING.
# ─────────────────────────────────────────────────────────

@api.route("/admin/sessions/<int:session_id>/report", methods=["GET"])
def session_report(session_id):
    """Returns full class roster with attendance status for a session."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    conn    = get_db_connection(db_path)

    # Get all users
    users = conn.execute("SELECT user_id, name FROM users ORDER BY name ASC").fetchall()

    # Get attendance records for this session
    logs = conn.execute("""
        SELECT user_id, status, method, timestamp
        FROM attendance
        WHERE session_id = ?
    """, (session_id,)).fetchall()
    conn.close()

    # Build a lookup: user_id → attendance record
    log_map = {row["user_id"]: row for row in logs}

    report = []
    for user in users:
        log = log_map.get(user["user_id"])
        report.append({
            "user_id":   user["user_id"],
            "name":      user["name"],
            "status":    log["status"]    if log else "PENDING",
            "method":    log["method"]    if log else "—",
            "timestamp": log["timestamp"] if log else "—",
        })

    return jsonify(report), 200


# ─────────────────────────────────────────────────────────
# ADMIN — VIEW ALL ATTENDANCE LOGS
# GET /admin/attendance
# ─────────────────────────────────────────────────────────

@api.route("/admin/attendance", methods=["GET"])
def admin_attendance():
    """
    Returns all attendance logs joined with user and session info.
    Admin only.
    """
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    conn    = get_db_connection(db_path)

    logs = conn.execute("""
        SELECT
            a.log_id,
            a.timestamp,
            a.method,
            a.status,
            a.date,
            a.day,
            u.name        AS user_name,
            s.session_name,
            s.start_time,
            s.end_time
        FROM attendance a
        JOIN users u        ON a.user_id    = u.user_id
        LEFT JOIN sessions s ON a.session_id = s.session_id
        ORDER BY a.timestamp DESC
    """).fetchall()

    conn.close()

    return jsonify([
        {
            "log_id":       row["log_id"],
            "timestamp":    row["timestamp"],
            "date":         row["date"],
            "day":          row["day"],
            "method":       row["method"],
            "status":       row["status"],
            "user_name":    row["user_name"],
            "session_name": row["session_name"],
            "start_time":   row["start_time"],
            "end_time":     row["end_time"]
        }
        for row in logs
    ]), 200


# ─────────────────────────────────────────────────────────
# ADMIN — DELETE SESSION
# DELETE /admin/sessions/<session_id>
# ─────────────────────────────────────────────────────────

@api.route("/admin/sessions/<int:session_id>", methods=["DELETE"])
def admin_delete_session(session_id):
    """Deletes a session by session_id. Admin only."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    delete_session(current_app.config["CHECKMATE_DB_PATH"], session_id)

    return jsonify({"status": "deleted", "session_id": session_id}), 200

# ─────────────────────────────────────────────────────────
# ADMIN — VIEW SYSTEM CONFIG
# GET /config
# ─────────────────────────────────────────────────────────

@api.route("/config", methods=["GET"])
def get_config():
    """Returns all system configuration settings. Admin only."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    settings = get_all_settings(current_app.config["CHECKMATE_DB_PATH"])

    return jsonify([
        {
            "key":         s["key"],
            "value":       s["value"],
            "description": s["description"]
        }
        for s in settings
    ]), 200


# ─────────────────────────────────────────────────────────
# ADMIN — UPDATE SYSTEM CONFIG
# POST /config/update
# ─────────────────────────────────────────────────────────

@api.route("/config/update", methods=["POST"])
def update_config():
    """Updates a system configuration setting. Admin only."""
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    data  = request.json
    key   = data.get("key")
    value = data.get("value")

    if not key or value is None:
        return jsonify({"error": "key and value are required"}), 400

    update_setting(current_app.config["CHECKMATE_DB_PATH"], key, str(value))

    # live config so running modules see the change immediately
    from config import runtime_config
    try:
        runtime_config[key] = int(value)
    except ValueError:
        runtime_config[key] = value


    return jsonify({"status": "updated", "key": key, "value": value}), 200


# ─────────────────────────────────────────────────────────
# ADMIN — SCAN NFC CARD (enrollment)
# GET /admin/nfc/scan
# Waits up to 15 seconds for a card tap on the Pi's NFC reader.
# Returns the card UID so the dashboard can link it to a user.
# ─────────────────────────────────────────────────────────

@api.route("/admin/nfc/scan", methods=["GET"])
def admin_nfc_scan():
    """
    Arms the NFC reader for enrollment mode and waits for a card tap.
    The next card tapped will NOT be processed as attendance —
    its UID is returned directly to the dashboard instead.
    Admin only.
    """
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        from attendance_manager import start_nfc_enrollment, get_enrolled_uid
        start_nfc_enrollment()
        uid = get_enrolled_uid(timeout=15)

        if uid:
            return jsonify({"uid": uid}), 200
        else:
            return jsonify({"error": "No card detected. Please tap the card and try again."}), 408

    except Exception as e:
        return jsonify({"error": f"NFC scan failed: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────
# ADMIN — CREATE NFC-ONLY USER
# POST /admin/users/create
# Creates a user without requiring the mobile app.
# Used for students who only have an NFC card (no phone).
# ─────────────────────────────────────────────────────────

@api.route("/admin/users/create", methods=["POST"])
def admin_create_user():
    """
    Creates an NFC-only user from the admin dashboard.
    Requires name, birthday, and nfc_id (from the NFC scan).
    Admin only.
    """
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    data     = request.json
    name     = data.get("name")
    birthday = data.get("birthday")
    nfc_id   = data.get("nfc_id")

    if not name or not birthday:
        return jsonify({"error": "Name and birthday are required"}), 400

    # Validate birthday format
    try:
        birth_date = datetime.strptime(birthday, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Birthday must be in YYYY-MM-DD format"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]

    # Check name is not already taken
    if get_user_by_name(db_path, name):
        return jsonify({"error": "A user with that name already exists"}), 400

    # NFC-only users get an auto-generated BLE ID (unused but keeps schema clean)
    # and an empty password hash (they cannot log in via the app)
    ble_id = generate_ble_uuid()

    user_id = create_user(
        db_path,
        name     = name,
        ble_id   = ble_id,
        nfc_id   = nfc_id,         # may be None if card wasn't scanned yet
        password_hash = "",        # NFC-only — no app login
        birthday = birthday,
        device_id = None
    )

    return jsonify({
        "user_id": user_id,
        "status":  "created",
        "type":    "nfc-only"
    }), 201


# ─────────────────────────────────────────────────────────
# ADMIN — LINK NFC CARD TO EXISTING USER
# POST /admin/users/<user_id>/link-nfc
# For BLE users who already registered via the app and now
# want to also use an NFC card.
# ─────────────────────────────────────────────────────────

@api.route("/admin/users/<int:user_id>/link-nfc", methods=["POST"])
def admin_link_nfc(user_id):
    """
    Links an NFC card UID to an existing user.
    Used for BLE users who want to add card-tap check-in.
    Admin only.
    """
    if not require_admin(request):
        return jsonify({"error": "Unauthorized"}), 401

    data   = request.json
    nfc_id = data.get("nfc_id")

    if not nfc_id:
        return jsonify({"error": "nfc_id is required"}), 400

    db_path = current_app.config["CHECKMATE_DB_PATH"]
    user    = get_user_by_id(db_path, user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Keep existing ble_id, just update nfc_id
    update_user_ids(db_path, user_id, user["ble_id"], nfc_id)

    return jsonify({
        "status":  "linked",
        "user_id": user_id,
        "nfc_id":  nfc_id
    }), 200
