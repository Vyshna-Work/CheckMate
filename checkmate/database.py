"""
database.py
-----------
Handles ALL database operations for the CheckMate system.
Used by the API server, Attendance Manager, BLE Scanner, and NFC Reader.
All SQL logic is isolated here so other modules stay clean.
"""

import sqlite3
from datetime import datetime


# ─────────────────────────────────────────────────────────
# CONNECTION HELPER
# ─────────────────────────────────────────────────────────

def get_db_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────
# DATABASE INITIALISATION
# ─────────────────────────────────────────────────────────

def initialize_database(db_path):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            password_hash TEXT    NOT NULL,
            ble_id        TEXT    UNIQUE,
            nfc_id        TEXT    UNIQUE,
            birthday      TEXT,
            device_id     TEXT,
            created_at    TEXT    DEFAULT (datetime('now'))
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name   TEXT    NOT NULL,
            date           TEXT    NOT NULL,
            day            TEXT    NOT NULL,
            start_time     TEXT    NOT NULL,
            end_time       TEXT    NOT NULL,
            late_threshold TEXT    NOT NULL,
            created_at     TEXT    DEFAULT (datetime('now'))
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            log_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            session_id INTEGER,
            date       TEXT    NOT NULL,
            day        TEXT    NOT NULL,
            timestamp  TEXT    NOT NULL,
            method     TEXT    NOT NULL CHECK (method IN ('BLE', 'NFC', 'AUTO')),
            status     TEXT    NOT NULL CHECK (status IN ('PRESENT', 'LATE', 'ABSENT')),
            FOREIGN KEY (user_id)    REFERENCES users(user_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            setting_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT    NOT NULL UNIQUE,
            value       TEXT    NOT NULL,
            description TEXT
        );
    """)

    default_settings = [
        ("rssi_threshold",   "-40", "Minimum RSSI value for BLE detection (dBm)"),
        ("duplicate_window", "5",   "Minutes before the same user can check in again"),
        ("cooldown_seconds", "3",   "Seconds to ignore repeated scans from the same ID"),
    ]
    for key, value, description in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (?, ?, ?)
        """, (key, value, description))

    existing_cols = [row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "created_at" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE users SET created_at = ? WHERE created_at IS NULL", (now,))

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────
# USER FUNCTIONS
# ─────────────────────────────────────────────────────────

def create_user(db_path, name, ble_id, nfc_id, password_hash, birthday, device_id):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO users (name, password_hash, ble_id, nfc_id, birthday, device_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, password_hash, ble_id, nfc_id, birthday, device_id, created_at))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def update_user_ids(db_path, user_id, ble_id, nfc_id):
    conn = get_db_connection(db_path)
    conn.execute("UPDATE users SET ble_id = ?, nfc_id = ? WHERE user_id = ?", (ble_id, nfc_id, user_id))
    conn.commit()
    conn.close()


def update_user_device(db_path, user_id, device_id):
    conn = get_db_connection(db_path)
    conn.execute("UPDATE users SET device_id = ? WHERE user_id = ?", (device_id, user_id))
    conn.commit()
    conn.close()


def get_user_by_id(db_path, user_id):
    conn = get_db_connection(db_path)
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def get_user_by_ble_id(db_path, ble_id):
    conn = get_db_connection(db_path)
    user = conn.execute("SELECT * FROM users WHERE ble_id = ?", (ble_id,)).fetchone()
    conn.close()
    return user


def get_user_by_nfc_id(db_path, nfc_id):
    conn = get_db_connection(db_path)
    user = conn.execute("SELECT * FROM users WHERE nfc_id = ?", (nfc_id,)).fetchone()
    conn.close()
    return user


def get_user_by_name(db_path, name):
    conn = get_db_connection(db_path)
    user = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
    conn.close()
    return user


def get_all_users(db_path):
    conn = get_db_connection(db_path)
    users = conn.execute("""
        SELECT user_id, name, ble_id, nfc_id, birthday, device_id, created_at
        FROM users ORDER BY user_id ASC
    """).fetchall()
    conn.close()
    return users


def delete_user(db_path, user_id):
    conn = get_db_connection(db_path)
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────
# ATTENDANCE FUNCTIONS
# ─────────────────────────────────────────────────────────

def create_attendance_log(db_path, user_id, session_id, method, status):
    now = datetime.now()
    date      = now.strftime("%Y-%m-%d")
    day       = now.strftime("%A")
    timestamp = now.strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_db_connection(db_path)
    conn.execute("""
        INSERT INTO attendance (user_id, session_id, date, day, timestamp, method, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, session_id, date, day, timestamp, method, status))
    conn.commit()
    conn.close()


def get_attendance_logs(db_path, user_id):
    conn = get_db_connection(db_path)
    logs = conn.execute("""
        SELECT timestamp, method, status FROM attendance
        WHERE user_id = ? ORDER BY timestamp DESC
    """, (user_id,)).fetchall()
    conn.close()
    return logs


def get_recent_attendance(db_path, user_id, window_minutes):
    """
    Checks if the user has already checked in within the duplicate window.
    Returns the most recent attendance entry if found, otherwise None.
    """
    conn = get_db_connection(db_path)
    record = conn.execute("""
        SELECT * FROM attendance
        WHERE user_id = ?
        AND timestamp >= datetime('now', ? || ' minutes')
        ORDER BY timestamp DESC
        LIMIT 1
    """, (user_id, f"-{window_minutes}")).fetchone()
    conn.close()
    return record


def get_attendance_for_session(db_path, user_id, session_id):
    """
    Checks if a user already has a PRESENT or LATE record for a specific session.
    Used by the Attendance Manager to prevent duplicate check-ins per session.
    Unlike get_recent_attendance, this is session-scoped — so a record in
    session A does not block check-in to session B.
    """
    conn = get_db_connection(db_path)
    record = conn.execute("""
        SELECT * FROM attendance
        WHERE user_id = ? AND session_id = ?
        AND status IN ('PRESENT', 'LATE')
        ORDER BY timestamp DESC
        LIMIT 1
    """, (user_id, session_id)).fetchone()
    conn.close()
    return record


def get_users_without_attendance(db_path, session_id):
    """
    Returns all users who have no attendance record for a given session.
    Used by the auto-absent system after a session ends.
    """
    conn = get_db_connection(db_path)
    users = conn.execute("""
        SELECT * FROM users
        WHERE user_id NOT IN (
            SELECT user_id FROM attendance WHERE session_id = ?
        )
    """, (session_id,)).fetchall()
    conn.close()
    return users


def mark_absent_for_session(db_path, session_id, session_date, session_day):
    """
    Inserts an ABSENT record for every user who has no attendance
    entry for the given session. Safe to call multiple times —
    duplicate check is handled by the INSERT query.
    """
    users = get_users_without_attendance(db_path, session_id)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_db_connection(db_path)
    for user in users:
        conn.execute("""
            INSERT INTO attendance (user_id, session_id, date, day, timestamp, method, status)
            SELECT ?, ?, ?, ?, ?, 'AUTO', 'ABSENT'
            WHERE NOT EXISTS (
                SELECT 1 FROM attendance
                WHERE user_id = ? AND session_id = ?
            )
        """, (user["user_id"], session_id, session_date, session_day, timestamp,
              user["user_id"], session_id))
    conn.commit()
    conn.close()


def delete_session(db_path, session_id):
    """Deletes a session by session_id."""
    conn = get_db_connection(db_path)
    conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────
# SESSION FUNCTIONS
# ─────────────────────────────────────────────────────────

def create_session(db_path, session_name, date, day, start_time, end_time, late_threshold):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (session_name, date, day, start_time, end_time, late_threshold)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_name, date, day, start_time, end_time, late_threshold))
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id


def get_all_sessions(db_path):
    conn = get_db_connection(db_path)
    sessions = conn.execute("""
        SELECT * FROM sessions ORDER BY date ASC, start_time ASC
    """).fetchall()
    conn.close()
    return sessions


def get_session_by_id(db_path, session_id):
    conn = get_db_connection(db_path)
    session = conn.execute(
        "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return session


def get_active_session(db_path, current_date, current_time):
    conn = get_db_connection(db_path)
    session = conn.execute("""
        SELECT * FROM sessions
        WHERE date = ?
        AND start_time <= ?
        AND end_time >= ?
        ORDER BY start_time ASC
        LIMIT 1
    """, (current_date, current_time, current_time)).fetchone()
    conn.close()
    return session


# ─────────────────────────────────────────────────────────
# SETTINGS FUNCTIONS
# ─────────────────────────────────────────────────────────

def get_setting(db_path, key):
    conn = get_db_connection(db_path)
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def get_all_settings(db_path):
    conn = get_db_connection(db_path)
    settings = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return settings


def update_setting(db_path, key, value):
    conn = get_db_connection(db_path)
    conn.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()
