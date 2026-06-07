# tests/test_registration.py
# Tests for the /users/register endpoint

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import create_app
from database import initialize_database
import tempfile
import pytest


@pytest.fixture
def client():
    """
    Pytest fixture that creates a temporary Flask test client
    with a temporary database file.
    """
    # Create a temporary file to act as a test database
    db_fd, db_path = tempfile.mkstemp()

    # Set environment variable so app uses this DB
    os.environ["CHECKMATE_DB"] = db_path

    # Create the Flask app
    app = create_app()
    app.config["TESTING"] = True

    # Initialize the temporary database
    initialize_database(db_path)

    # Create a test client
    with app.test_client() as client:
        yield client

    # Cleanup: remove temporary DB file
    os.close(db_fd)
    os.remove(db_path)


def test_register_success(client):
    """
    Test that a user can register successfully.
    """
    response = client.post("/users/register", json={
        "name": "Test User",
        "password": "1234"
    })

    data = response.get_json()

    assert response.status_code == 201
    assert "user_id" in data
    assert "ble_id" in data
    assert data["status"] == "registered"


def test_register_missing_name(client):
    """
    Test that registration fails if name is missing.
    """
    response = client.post("/users/register", json={})

    data = response.get_json()

    assert response.status_code == 400
    assert data["error"] == "Name and password are required"


