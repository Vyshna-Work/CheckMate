import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import tempfile
import pytest
from app import create_app
from database import initialize_database, create_user


@pytest.fixture
def client():
    """
    Creates a temporary Flask test client with a temporary database.
    """
    db_fd, db_path = tempfile.mkstemp()
    os.environ["CHECKMATE_DB"] = db_path

    app = create_app()
    app.config["TESTING"] = True

    initialize_database(db_path)

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.remove(db_path)


# -----------------------------
# BLE Attendance Logging
# -----------------------------
def test_attendance_ble_success(client):
    """
    Should log attendance using BLE ID.
    """
    user_id = create_user(
        os.environ["CHECKMATE_DB"],
        "Test User",
        "BLE123",
        None,
        "test_hash"
    )

    response = client.post("/attendance/log", json={
        "method": "ble",
        "identifier": "BLE123"
    })

    data = response.get_json()

    assert response.status_code == 201
    assert data["status"] == "logged"
    assert data["user_id"] == user_id


# -----------------------------
# NFC Attendance Logging
# -----------------------------
def test_attendance_nfc_success(client):
    """
    Should log attendance using NFC ID.
    """
    user_id = create_user(
        os.environ["CHECKMATE_DB"],
        "Test User",
        "BLE999",
        "NFC555",
        "test_hash"
    )

    response = client.post("/attendance/log", json={
        "method": "nfc",
        "identifier": "NFC555"
    })

    data = response.get_json()

    assert response.status_code == 201
    assert data["status"] == "logged"
    assert data["user_id"] == user_id


# -----------------------------
# Unknown User
# -----------------------------
def test_attendance_unknown_user(client):
    """
    Should return 404 if BLE/NFC ID does not match any user.
    """
    response = client.post("/attendance/log", json={
        "method": "ble",
        "identifier": "UNKNOWN123"
    })

    data = response.get_json()

    assert response.status_code == 404
    assert data["error"] == "User not found"


# -----------------------------
# Missing Fields
# -----------------------------
def test_attendance_missing_fields(client):
    """
    Should return 400 if method or identifier is missing.
    """
    response = client.post("/attendance/log", json={
        "method": "ble"
    })

    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "method and identifier are required"


# -----------------------------
# Invalid Method
# -----------------------------
def test_attendance_invalid_method(client):
    """
    Should return 400 if method is not 'ble' or 'nfc'.
    """
    response = client.post("/attendance/log", json={
        "method": "wifi",
        "identifier": "123"
    })

    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Invalid method"
