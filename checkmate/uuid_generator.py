"""
uuid_generator.py
-----------------
Generates unique BLE UUIDs for new users.
Kept separate so the API stays clean and modular.
"""

import uuid


def generate_ble_uuid():
    """
    Generates a unique BLE UUID for a new user.
    Returns a string like: '550e8400-e29b-41d4-a716-446655440000'
    """
    return str(uuid.uuid4())
