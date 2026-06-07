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


def test_update_ids_missing_user_id(client):
    """
    Should return 400 if user_id is missing.
    """
    response = client.post("/users/update-ids", json={
        "ble_id": "BLE123"
    })

    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "user_id is required"


def test_update_ids_success(client):
    """
    Should update BLE and NFC IDs successfully.
    """
    # First create a user
    user_id = create_user(
        os.environ["CHECKMATE_DB"],
        "Test User",
        "OLD_BLE",
        None,
        "test_hash"
    )

    # Now update the IDs
    response = client.post("/users/update-ids", json={
        "user_id": user_id,
        "ble_id": "NEW_BLE",
        "nfc_id": "NEW_NFC"
    })

    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "updated"


def test_update_only_ble(client):
    """
    Should update only BLE ID.
    """
    user_id = create_user(
        os.environ["CHECKMATE_DB"],
        "Test User",
        "OLD_BLE",
        None,
        "test_hash"
    )

    response = client.post("/users/update-ids", json={
        "user_id": user_id,
        "ble_id": "UPDATED_BLE"
    })

    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "updated"


def test_update_only_nfc(client):
    """
    Should update only NFC ID.
    """
    user_id = create_user(
        os.environ["CHECKMATE_DB"],
        "Test User",
        "OLD_BLE",
        None,
        "test_hash"
    )

    response = client.post("/users/update-ids", json={
        "user_id": user_id,
        "nfc_id": "UPDATED_NFC"
    })

    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "updated"
