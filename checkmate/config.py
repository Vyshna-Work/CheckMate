# config.py
# Central configuration file for the CheckMate system.
# All modules import their settings from here.
# Values can also be overridden by the settings table in the database.

# ─────────────────────────────────────────────────────────
# GPIO PIN ASSIGNMENTS  (BCM numbering)
# Raspberry Pi 4 Model B
# ─────────────────────────────────────────────────────────

# ── I2C (shared bus — LCD backpack + PN532 both on bus 1) ──
# SDA → GPIO2 (physical pin 3)
# SCL → GPIO3 (physical pin 5)
I2C_BUS          = 1
LCD_I2C_ADDRESS  = 0x27   # PCF8574 backpack for 20×4 LCD
NFC_I2C_ADDRESS  = 0x24   # PN532 in I2C mode

# ── Buttons (active LOW, internal pull-up enabled) ──
# Physical pin → BCM
BTN_UP     = 4    # Red button     (physical pin 7)
BTN_DOWN   = 17   # Purple button  (physical pin 11)
BTN_EMPTY  = 27   # Brown button   (physical pin 13, reserved)
BTN_SELECT = 22   # Yellow button  (physical pin 15)

# ── RGB LED (common cathode, built-in resistors) ──
# Cathode → GND
RGB_RED   = 10    # GPIO10 (physical pin 19)
RGB_GREEN = 9     # GPIO9  (physical pin 21)
RGB_BLUE  = 11    # GPIO11 (physical pin 23)

# ── Audio — PAM8402 amplifier ──
# A+ → GPIO18 (physical pin 12, hardware PWM)
# A− → GND
# No shutdown pin used.
# OS-level setup required in /boot/config.txt:
#   dtoverlay=audremap,pins_18_19
AUDIO_PWM_PIN = 18

# ─────────────────────────────────────────────────────────
# BLE SETTINGS
# ─────────────────────────────────────────────────────────

# The custom 128-bit service UUID assigned to the CheckMate system.
# Only BLE advertisements containing this UUID will be processed.
# All other devices (phones, earbuds, smartwatches) are ignored.
SYSTEM_UUID = "12345678-1234-5678-1234-56789abcdef0"

# Minimum signal strength in dBm for a BLE device to be accepted.
# Devices weaker than this are too far away — ignore them.
# -70 dBm is roughly 3–5 metres depending on environment.

RSSI_THRESHOLD = -50

# How many seconds to ignore the same BLE device after detecting it.
# Prevents the same student from being logged multiple times
# if they stay near the reader.
DETECTION_COOLDOWN = 60  # seconds

# ─────────────────────────────────────────────────────────
# API SETTINGS
# ─────────────────────────────────────────────────────────

# The local API server URL running on the Raspberry Pi.
API_URL = "http://127.0.0.1:5000/attendance/log"

# ─────────────────────────────────────────────────────────
# DATABASE SETTINGS
# ─────────────────────────────────────────────────────────

# Path to the SQLite database file.
DB_PATH = "checkmate_api_test.db"

#------------------------------------------------------------
runtime_config = {
    "rssi_threshold": -50,
    "duplicate_window": 5,
    "cooldown_seconds": 3,
}
