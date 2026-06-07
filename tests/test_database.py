import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import tempfile
import pytest
from database import (
    initialize_database,
    create_user,
    update_user_ids,
    get_user_by_id,
    get_user_by_ble_id,
    get_user_by_nfc_id,
    create_attendance_log,
    get_attendance_logs
)


@pytest.fixture
def db_path():
    """
    Creates a temporary database for testing.
    """
    fd, path = tempfile.mkstemp()
    initialize_database(path)
    yield path
    os.close(fd)
    os.remove(path)


# -----------------------------
# USER CREATION
# -----------------------------
def test_create_user(db_path):
    user_id = create_user(db_path, "Alice", "BLE001", "NFC001", "test_hash")
    user = get_user_by_id(db_path, user_id)

    assert user is not None
    assert user["name"] == "Alice"
    assert user["ble_id"] == "BLE001"
    assert user["nfc_id"] == "NFC001"
    assert user["password_hash"] == "test_hash"


# -----------------------------
# UPDATE USER IDS
# -----------------------------
def test_update_user_ids(db_path):
    user_id = create_user(db_path, "Bob", "OLD_BLE", None, "test_hash")

    update_user_ids(db_path, user_id, "NEW_BLE", "NEW_NFC")
    user = get_user_by_id(db_path, user_id)

    assert user["ble_id"] == "NEW_BLE"
    assert user["nfc_id"] == "NEW_NFC"


# -----------------------------
# LOOKUP BY BLE
# -----------------------------
def test_get_user_by_ble_id(db_path):
    user_id = create_user(db_path, "Charlie", "BLE777", None, "test_hash")

    user = get_user_by_ble_id(db_path, "BLE777")

    assert user is not None
    assert user["user_id"] == user_id
    assert user["name"] == "Charlie"


# -----------------------------
# LOOKUP BY NFC
# -----------------------------
def test_get_user_by_nfc_id(db_path):
    user_id = create_user(db_path, "Dana", None, "NFC999", "test_hash")

    user = get_user_by_nfc_id(db_path, "NFC999")

    assert user is not None
    assert user["user_id"] == user_id
    assert user["name"] == "Dana"


# -----------------------------
# ATTENDANCE LOGGING
# -----------------------------
def test_create_attendance_log(db_path):
    user_id = create_user(db_path, "Eve", "BLE123", None, "test_hash")

    create_attendance_log(db_path, user_id, "BLE")
    logs = get_attendance_logs(db_path, user_id)

    assert len(logs) == 1
    assert logs[0]["method"] == "BLE"


# -----------------------------
# MULTIPLE ATTENDANCE LOGS
# -----------------------------
def test_multiple_attendance_logs(db_path):
    user_id = create_user(db_path, "Frank", "BLE555", None, "test_hash")

    create_attendance_log(db_path, user_id, "BLE")
    create_attendance_log(db_path, user_id, "NFC")

    logs = get_attendance_logs(db_path, user_id)

    assert len(logs) == 2
    assert logs[0]["method"] in ["BLE", "NFC"]
    assert logs[1]["method"] in ["BLE", "NFC"]
