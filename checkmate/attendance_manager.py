"""
attendance_manager.py
---------------------
Central decision-making component for the CheckMate attendance system.
Receives events from BLE Scanner and NFC Reader, validates users,
applies attendance rules, prevents duplicates, and triggers
LCD and audio feedback.
"""

import logging
import queue
from datetime import datetime
from database import (
    get_user_by_ble_id,
    get_user_by_nfc_id,
    get_recent_attendance,
    create_attendance_log,
    get_active_session,
    get_setting
)
from audio_controller import AudioController
from ui_controller import UIController
from config import DB_PATH, runtime_config


logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# NFC ENROLLMENT STATE
# Used by the dashboard to capture the next card tap
# instead of processing it as attendance.
# ─────────────────────────────────────────────────────────

_enrollment_active = False          # True while dashboard is waiting for a tap
_enrollment_queue  = queue.Queue(maxsize=1)  # holds the captured UID


def start_nfc_enrollment():
    """Called by the API route — arms the system to capture the next card tap."""
    global _enrollment_active
    # Clear any stale UID from a previous scan
    while not _enrollment_queue.empty():
        try:
            _enrollment_queue.get_nowait()
        except queue.Empty:
            break
    _enrollment_active = True


def get_enrolled_uid(timeout=15):
    """
    Blocks until a card is tapped or timeout expires.
    Returns the UID string if successful, None if timed out.
    """
    global _enrollment_active
    try:
        uid = _enrollment_queue.get(timeout=timeout)
        return uid
    except queue.Empty:
        return None
    finally:
        _enrollment_active = False


# ─────────────────────────────────────────────────────────
# MODULE INSTANCES
# ─────────────────────────────────────────────────────────

audio = AudioController(sounds_folder="sounds", enabled=True)
ui    = UIController()

# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────

DUPLICATE_WINDOW_MINUTES = 5
RSSI_THRESHOLD           = -50
COOLDOWN_SECONDS         = 3


def load_config():
    """Loads config from the settings table. Falls back to defaults."""
    global DUPLICATE_WINDOW_MINUTES, RSSI_THRESHOLD, COOLDOWN_SECONDS
    try:
        rssi = get_setting(DB_PATH, "rssi_threshold")
        dup  = get_setting(DB_PATH, "duplicate_window")
        cool = get_setting(DB_PATH, "cooldown_seconds")
        if rssi:  RSSI_THRESHOLD           = int(rssi)
        if dup:   DUPLICATE_WINDOW_MINUTES = int(dup)
        if cool:  COOLDOWN_SECONDS         = int(cool)

        # sync live config so all modules see updated values immediately
        runtime_config["rssi_threshold"]   = int(rssi)  if rssi else -50
        runtime_config["duplicate_window"] = int(dup)   if dup  else 5
        runtime_config["cooldown_seconds"] = int(cool)  if cool else 3

        logger.info(f"Config loaded — RSSI: {RSSI_THRESHOLD}, Duplicate window: {DUPLICATE_WINDOW_MINUTES}min, Cooldown: {COOLDOWN_SECONDS}s")
    except Exception as e:
        logger.warning(f"Could not load config from DB, using defaults. Error: {e}")


# ─────────────────────────────────────────────────────────
# INTERNAL STATE
# ─────────────────────────────────────────────────────────

# Tracks the last time each BLE UUID or NFC UID was processed.
# Key: identifier string (UUID or UID), Value: datetime of last seen.
# Used by is_on_cooldown() to block rapid repeated check-ins.
_last_seen = {}


def is_on_cooldown(identifier):
    """
    Returns True if this identifier was seen too recently and should be ignored.
    Side effect: if NOT on cooldown, records the current time as the last seen
    time so the next call within COOLDOWN_SECONDS will be blocked.
    """
    if identifier in _last_seen:
        elapsed = (datetime.now() - _last_seen[identifier]).total_seconds()
        if elapsed < runtime_config["cooldown_seconds"]:
            return True
    # Not on cooldown — stamp the time now so duplicates are blocked next
    _last_seen[identifier] = datetime.now()
    return False


def is_birthday(user):
    """Returns True if today is the student's birthday."""
    try:
        birthday = user["birthday"]
        if not birthday:
            return False
        today      = datetime.now()
        birth_date = datetime.strptime(birthday, "%Y-%m-%d")
        return today.month == birth_date.month and today.day == birth_date.day
    except Exception:
        return False


# ─────────────────────────────────────────────────────────
# CORE CHECK-IN LOGIC
# ─────────────────────────────────────────────────────────

def process_check_in(user, method):
    """
    Handles the full check-in process.
    1. Duplicate check
    2. Find active session
    3. Determine PRESENT or LATE
    4. Log attendance
    5. LCD + audio feedback
    6. Birthday check
    """
    user_id   = user["user_id"]
    user_name = user["name"]

    # Duplicate check
    recent = get_recent_attendance(DB_PATH, user_id, runtime_config["duplicate_window"])
    if recent:
        ui.show_warning("Already checked in")
        audio.play_warning()
        logger.info(f"Duplicate blocked: {user_name}")
        return

    # Find active session
    now          = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    session = get_active_session(DB_PATH, current_date, current_time)
    if not session:
        ui.show_error("No active session")
        audio.play_error()
        logger.info(f"No active session for: {user_name}")
        return

    # Determine status
    status = "PRESENT" if current_time <= session["late_threshold"] else "LATE"

    # Log attendance
    create_attendance_log(DB_PATH, user_id, session["session_id"], method, status)

    # Feedback
    if status == "PRESENT":
        ui.show_success(user_name)
        audio.play_success(user_name)
    else:
        ui.show_late(user_name)
        audio.play_late(user_name)

    logger.info(f"Logged — {user_name}, {method}, {status}, {session['session_name']}")

    # Birthday check
    if is_birthday(user):
        logger.info(f"Happy birthday, {user_name}!")
        audio.play_birthday(user_name)


# ─────────────────────────────────────────────────────────
# EVENT HANDLERS
# ─────────────────────────────────────────────────────────

def on_ble_detected(user_ble_id, rssi):
    """Called by BLE Scanner when an iBeacon is detected."""
    logger.info(f"[BLE] ID: {user_ble_id}, RSSI: {rssi}")

    if rssi < runtime_config["rssi_threshold"]:
        logger.debug(f"[BLE] Too weak ({rssi} dBm), ignoring.")
        return

    if is_on_cooldown(user_ble_id):
        logger.debug(f"[BLE] On cooldown, ignoring.")
        return

    user = get_user_by_ble_id(DB_PATH, user_ble_id)
    if not user:
        ui.show_error("Unrecognised device")
        audio.play_error()
        return

    process_check_in(user, method="BLE")


def on_nfc_detected(user_nfc_uid):
    """Called by NFC Reader when a card is tapped."""
    logger.info(f"[NFC] UID: {user_nfc_uid}")

    # If the dashboard is waiting to enroll a card, capture the UID
    # and skip normal attendance processing entirely.
    if _enrollment_active:
        try:
            _enrollment_queue.put_nowait(user_nfc_uid)
        except queue.Full:
            pass
        return

    if is_on_cooldown(user_nfc_uid):
        logger.debug(f"[NFC] On cooldown, ignoring.")
        return

    user = get_user_by_nfc_id(DB_PATH, user_nfc_uid)
    if not user:
        ui.show_error("Unrecognised card")
        audio.play_error()
        return

    process_check_in(user, method="NFC")
