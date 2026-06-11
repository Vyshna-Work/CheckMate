# ============================================================
# main.py
# PURPOSE: Entry point for the CheckMate hardware system.
#          Starts all modules and connects them together.
#          Each module runs in its own background thread so
#          they all work simultaneously without blocking each other.
#
# MODULES RUNNING:
#   - NFC Reader         → detects card taps → Attendance Manager
#   - BLE Scanner        → detects student phones → Attendance Manager
#   - Attendance Manager → validates, logs, triggers LCD + audio feedback
#   - UI Controller      → drives 20x4 LCD, RGB LED, and 4 buttons
#   - Audio Controller   → plays personalised greetings via PAM8402 amp
#   - API Server         → Flask REST API for mobile app communication
#   - Session Monitor    → marks absent students when session ends
#
# HARDWARE (Raspberry Pi 4 Model B):
#   - PN532 NFC reader   → I2C bus 1 (GPIO2/GPIO3), address 0x24
#   - 20x4 LCD           → I2C bus 1 (GPIO2/GPIO3), address 0x27
#   - RGB LED            → GPIO10 (R), GPIO9 (G), GPIO11 (B)
#   - 4 buttons          → GPIO4, 17, 27, 22 (BCM, active LOW)
#   - PAM8402 amplifier  → A+ on GPIO18 (PWM audio), A- to GND
# ============================================================

import threading
import logging
import time

from nfc_reader import NFCReaderModule
from ble_scanner import BLEScannerModule
from attendance_manager import on_nfc_detected, on_ble_detected, load_config, ui
from database import initialize_database, get_all_sessions, mark_absent_for_session
from config import DB_PATH
from app import create_app
from datetime import datetime

# Show timestamped INFO logs in the terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# STEP 1 — Initialise the database
# Creates all tables if they don't exist yet.
# ─────────────────────────────────────────────────────────

logger.info("Initialising database...")
initialize_database(DB_PATH)
logger.info("Database ready.")


# ─────────────────────────────────────────────────────────
# STEP 2 — Load config from database into Attendance Manager
# Pulls RSSI threshold, duplicate window, cooldown from
# the settings table so they can be changed without code edits.
# ─────────────────────────────────────────────────────────

load_config()


# ─────────────────────────────────────────────────────────
# STEP 3 — Set up the NFC Reader
# Card taps → on_nfc_detected() → Attendance Manager
# ─────────────────────────────────────────────────────────

nfc_module = NFCReaderModule(
    on_nfc_detected=on_nfc_detected,  # connected to Attendance Manager
    cooldown_seconds=5.0,             # ignore same card for 5 seconds
    polling_interval=0.5,             # check for cards every 0.5 seconds
)


# ─────────────────────────────────────────────────────────
# STEP 4 — Set up the BLE Scanner
# Student phone detections → on_ble_detected() → Attendance Manager
# ─────────────────────────────────────────────────────────

ble_module = BLEScannerModule(
    on_ble_detected=on_ble_detected,  # connected to Attendance Manager
)


# ─────────────────────────────────────────────────────────
# STEP 5 — Set up the API Server (Flask)
# Runs in background so mobile app can register users,
# log attendance, and retrieve data.
# ─────────────────────────────────────────────────────────

flask_app = create_app()

def run_api_server():
    """Runs the Flask API server in a background thread."""
    logger.info("Starting API server on port 5000...")
    flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)


# ─────────────────────────────────────────────────────────
# STEP 6 — Start all threads
# Each module runs as a daemon thread — stops automatically
# when the main program exits.
# ─────────────────────────────────────────────────────────

# Start API Server thread
api_thread = threading.Thread(target=run_api_server, daemon=True, name="APIServer")
api_thread.start()
logger.info("API Server thread started.")

# Start BLE Scanner thread
ble_thread = threading.Thread(target=ble_module.start, daemon=True, name="BLEScanner")
ble_thread.start()
logger.info("BLE Scanner thread started.")

# Start NFC Reader thread (only if hardware initialises successfully)
if nfc_module.initialise():
    logger.info("NFC Reader hardware ready.")
    nfc_thread = threading.Thread(target=nfc_module.start, daemon=True, name="NFCReader")
    nfc_thread.start()
    logger.info("NFC Reader thread started.")
else:
    logger.error("Could not connect to PN532. Check I2C wiring.")
    logger.warning("System running in BLE-only mode — NFC unavailable.")

# ─────────────────────────────────────────────────────────
# STEP 6b — Session Monitor
# Runs every 60 seconds. When a session ends, marks all
# students with no attendance record as ABSENT automatically.
# ─────────────────────────────────────────────────────────

def session_monitor():
    """
    Runs every 60 seconds. Checks if any session ended in the last minute.
    If so, marks all students without attendance as ABSENT.
    """
    checked_sessions = set()

    while True:
        time.sleep(60)
        try:
            now          = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")

            sessions = get_all_sessions(DB_PATH)
            for session in sessions:
                if session["session_id"] in checked_sessions:
                    continue
                if session["date"] == current_date:
                    if session["end_time"] <= current_time:
                        mark_absent_for_session(
                            DB_PATH,
                            session["session_id"],
                            session["date"],
                            session["day"]
                        )
                        checked_sessions.add(session["session_id"])
                        logger.info(f"Auto-absent marked for session: {session['session_name']}")
        except Exception as e:
            logger.warning(f"Session monitor error: {e}")

monitor_thread = threading.Thread(target=session_monitor, daemon=True, name="SessionMonitor")
monitor_thread.start()
logger.info("Session monitor thread started.")

# ─────────────────────────────────────────────────────────
# STEP 7 — Keep main thread alive
# All modules run in daemon threads.
# Main thread just waits here. Ctrl+C stops everything.
# ─────────────────────────────────────────────────────────

logger.info("CheckMate system running. Press Ctrl+C to stop.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Shutdown signal received.")
    nfc_module.stop()
    ble_module.stop()
    ui.cleanup()
    logger.info("CheckMate system stopped cleanly.")
