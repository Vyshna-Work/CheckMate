"""
database.py
-----------
This module handles ALL database operations for the CheckMate system.
It is fully isolated so the API, BLE scanner, NFC reader, and Attendance Manager
can all use the same database layer later.
"""

import sqlite3
from datetime import datetime


# ---------------------------------------------------------
# Helper function: open a connection to the SQLite database
# ---------------------------------------------------------
def get_db_connection(db_path):
    """
    Opens a connection to the SQLite database.
    db_path comes from app.config["CHECKMATE_DB_PATH"].
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # allows dict-like access to rows
    return conn


# ---------------------------------------------------------
# Initialize database tables (Users + Attendance)
# ---------------------------------------------------------
def initialize_database(db_path):
    """
    Creates the required tables if they do not exist.
    This function is safe to call every time the API starts.
    """

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            ble_id TEXT UNIQUE,
            nfc_id TEXT UNIQUE,
            birthday TEXT,
            device_id TEXT
            
        );
    """)

    # Attendance logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_id INTEGER,       
            timestamp TEXT NOT NULL,
            method TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
    """)
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            date TEXT NOT NULL,          -- YYYY-MM-DD
            day TEXT NOT NULL,           -- e.g. Monday
            start_time TEXT NOT NULL,    -- HH:MM
            end_time TEXT NOT NULL,      -- HH:MM
            late_threshold TEXT NOT NULL, -- HH:MM
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# CRUD FUNCTIONS FOR USERS
# ---------------------------------------------------------

def create_user(db_path, name, ble_id, nfc_id, password_hash, birthday, device_id):

    """
    Inserts a new user into the database.
    Returns the new user's ID.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (name, password_hash, ble_id, nfc_id, birthday, device_id)
    VALUES (?, ?, ?, ?, ?, ?)
""", (name, password_hash, ble_id, nfc_id, birthday, device_id))


    conn.commit()
    user_id = cursor.lastrowid # returns the id of the most recently inserted row. 
    conn.close()

    return user_id


def update_user_ids(db_path, user_id, ble_id, nfc_id):
    """
    Updates BLE and NFC IDs for an existing user.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET ble_id = ?, nfc_id = ?
        WHERE user_id = ?
    """, (ble_id, nfc_id, user_id))

    conn.commit()
    conn.close()


def get_user_by_id(db_path, user_id):
    """
    Returns a user record by user_id.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    conn.close()
    return user


def get_user_by_ble_id(db_path, ble_id):
    """
    Returns a user record matching the BLE ID.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE ble_id = ?", (ble_id,))
    user = cursor.fetchone()

    conn.close()
    return user


def get_user_by_nfc_id(db_path, nfc_id):
    """
    Returns a user record matching the NFC UID.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE nfc_id = ?", (nfc_id,))
    user = cursor.fetchone()

    conn.close()
    return user

def get_user_by_name(db_path, name):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
    user = cursor.fetchone()

    conn.close()
    return user



# ---------------------------------------------------------
# ATTENDANCE LOG FUNCTIONS
# ---------------------------------------------------------

def create_attendance_log(db_path, user_id, session_id, method, status):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO attendance (user_id, session_id, timestamp, method, status)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, session_id, timestamp, method, status))

    conn.commit()
    conn.close()

def get_attendance_logs(db_path, user_id):
    """
    Returns all attendance logs for a user.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, method, status
        FROM attendance
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """, (user_id,))

    logs = cursor.fetchall()
    conn.close()

    return logs
# ---------------------------------------------------------
# ADMIN FUNCTIONS (LIST + DELETE USERS)
# ---------------------------------------------------------

def get_all_users(db_path):
    """
    Returns all users in the database.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, name, ble_id, nfc_id, birthday, device_id
        FROM users
        ORDER BY user_id ASC
    """)

    users = cursor.fetchall()
    conn.close()
    return users


def delete_user(db_path, user_id):
    """
    Deletes a user by user_id.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def update_user_device(db_path, user_id, device_id):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET device_id = ? WHERE user_id = ?", (device_id, user_id))
    conn.commit()
    conn.close()
    
# ---------------------------------------------------------
# SESSION FUNCTIONS
# ---------------------------------------------------------

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
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM sessions
        ORDER BY date ASC, start_time ASC
    """)

    sessions = cursor.fetchall()
    conn.close()
    return sessions


def get_session_by_id(db_path, session_id):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()

    conn.close()
    return session

def get_active_session(db_path, current_date, current_time):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM sessions
        WHERE date = ?
        AND start_time <= ?
        AND end_time >= ?
        ORDER BY start_time ASC
        LIMIT 1
    """, (current_date, current_time, current_time))

    session = cursor.fetchone()
    conn.close()
    return session
