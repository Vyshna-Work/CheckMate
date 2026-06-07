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
            nfc_id TEXT UNIQUE
            
        );
    """)

    # Attendance logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            method TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# CRUD FUNCTIONS FOR USERS
# ---------------------------------------------------------

def create_user(db_path, name, ble_id, nfc_id, password_hash):

    """
    Inserts a new user into the database.
    Returns the new user's ID.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (name, password_hash, ble_id, nfc_id)
    VALUES (?, ?, ?, ?)
""", (name, password_hash, ble_id, nfc_id))


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

def create_attendance_log(db_path, user_id, method):
    """
    Creates a new attendance log entry.
    method = "BLE" or "NFC"
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    timestamp = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO attendance (user_id, timestamp, method)
        VALUES (?, ?, ?)
    """, (user_id, timestamp, method))

    conn.commit()
    conn.close()


def get_attendance_logs(db_path, user_id):
    """
    Returns all attendance logs for a user.
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT timestamp, method
        FROM attendance
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """, (user_id,))

    logs = cursor.fetchall()
    conn.close()

    return logs
