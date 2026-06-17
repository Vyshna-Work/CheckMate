# Project Overview

CheckMate is a smart attendance system built for classroom use. It automatically detects students using Bluetooth Low Energy (BLE) from their Android phones and records attendance without any manual action. If BLE fails, students tap their university NFC card on the device as a backup. Check-in completes in under 3 seconds. The teacher does not need to do anything.

The system runs on a Raspberry Pi 4 Model B and provides instant feedback through a 20×4 LCD screen, an RGB LED, and a speaker with personalised audio greetings. An admin dashboard is accessible from any browser on the same network.

---

## Team — The Cyber Guardians

| Name | Student No. | Role |
|---|---|---|
| Salman Al-Odani | 5638364 | Software & Hardware Specialist — Flask API, Android App |
| Ondřej Urbánek | 5679664 | Hardware & Software Engineer — Wiring, Video, System integretion. UI Controller |
| Aisha Binti Julkifli | 5639603 | Team Leader & Software Specialist — BLE Scanner Module, Group Portfolio|
| Sana Safaei Bonab | 5723213 |Software Specialist| NFC Module, Logo design, group portfolio|
| Sjonly Sherwood | 5653274 | Software Specialist — Audio Controller |
| Vyshna Attadappa Puthanveettil | 5659426 |Software abd Daiunrbtsg Attendence manager, system inegretion assistance, and related documentation

|

---

## How It Works

1. Student walks into the classroom with the CheckMate Android app running in the background
2. The Raspberry Pi detects the student's unique BLE iBeacon UUID automatically
3. The Attendance Manager looks up the UUID in the database and determines PRESENT or LATE
4. The LCD shows the student's name and status, the LED lights up, and a personalised greeting plays
5. If BLE fails — student taps their NFC university card on the reader (same outcome)
6. Teachers access the admin dashboard from any browser to view live attendance and reports

---

## Key Features

- **Automatic BLE check-in** — detects students passively via iBeacon, no action needed
- **NFC card backup** — tap any registered MIFARE university card as a fallback
- **Personalised audio greetings** — birthday mode, late arrival (teacher voices), first-to-arrive (team voices), invalid card
- **LCD startup animation** — wave wipe effect and CheckMate logo on boot
- **PRESENT / LATE tracking** — compares check-in time against the session's late threshold
- **Duplicate prevention** — same student cannot check in twice per session
- **Auto absent marking** — students who do not check in are marked ABSENT when the session ends
- **Offline mode** — SQLite buffer stores records when Wi-Fi is unavailable
- **Admin dashboard** — session management, live roster, session reports, CSV export
- **Device lock security** — each student account is bound to one phone

---

## Hardware

| Component | Role |
|---|---|
| Raspberry Pi 4 Model B (4GB) | Central processing unit |
| PN532 NFC Reader (I2C, address 0x24) | Manual card tap backup |
| 20×4 LCD Display + PCF8574 I2C backpack (address 0x27) | Status display |
| PAM8302 Amplifier + Speaker 4Ω 3W | Audio feedback |
| RGB LED (common cathode) | Visual status indicator |
| 4× Colour Push Buttons (Yellow×2, Green, Red) | Menu navigation |
| Raspberry Pi Official USB-C PSU (5.1V 3A) | Power supply |
| 3D Printed PLA Casing | Enclosure |

### GPIO Pin Reference (BCM)

| GPIO | Component | Direction |
|---|---|---|
| GPIO 2 (SDA) | LCD + PN532 (shared I2C bus) | Bidirectional |
| GPIO 3 (SCL) | LCD + PN532 (shared I2C bus) | Bidirectional |
| GPIO 4 | Button — Up (Yellow) | Input, active LOW |
| GPIO 9 | RGB LED — Green | Output |
| GPIO 10 | RGB LED — Red | Output |
| GPIO 11 | RGB LED — Blue | Output |
| GPIO 17 | Button — Down (Yellow) | Input, active LOW |
| GPIO 18 | PAM8302 Amplifier (A+) | PWM audio output |
| GPIO 22 | Button — Select (Green) | Input, active LOW |
| GPIO 27 | Button — Placeholder (Red) | Input, active LOW |

---

## Software Modules

| File | Description |
|---|---|
| `main.py` | Entry point — initialises DB, starts all threads |
| `ble_scanner.py` | iBeacon BLE scanning via Bleak |
| `nfc_reader.py` | PN532 polling via smbus2 |
| `attendance_manager.py` | Core decision logic — validates, logs, triggers feedback |
| `ui_controller.py` | 20×4 LCD control, button input, RGB LED |
| `audio_controller.py` | Non-blocking audio playback via ffplay |
| `app.py` + `routes.py` | Flask REST API server |
| `database.py` | All SQLite CRUD operations |
| `config.py` | Central GPIO, I2C, BLE, and DB configuration |
| `uuid_generator.py` | Generates unique BLE UUIDs for new users |

---

## Installation

### Requirements

- Raspberry Pi 4 running Raspberry Pi OS (64-bit Bookworm)
- I2C enabled (`sudo raspi-config` → Interface Options → I2C → Enable)
- Python 3 (included with Raspberry Pi OS)

### Install Python dependencies

```bash
pip install flask bleak smbus2 RPLCD RPi.GPIO werkzeug python-dotenv --break-system-packages
sudo apt install ffmpeg
```

### Enable PWM audio output

Add the following line to `/boot/firmware/config.txt` and reboot:

```
dtoverlay=audremap,pins_18_19
```

### Environment configuration

Create a `.env` file in the project folder:

```
ADMIN_KEY=your_secret_key_here
```

### Audio files

Place all `.m4a` audio files in a `sounds/` subfolder inside the project directory.

---

## Running the System

The system does not start automatically on power-on. Each time the device is powered up:

1. Connect to the Raspberry Pi via SSH (e.g. using the VS Code Remote-SSH extension)
2. Navigate to the project folder and activate the virtual environment:

```bash
cd ~/checkmate
source venv/bin/activate
```

3. Start the system:

```bash
python main.py
```

The LCD will play the CheckMate startup animation, then show `Status: scanning...` — the system is ready.

To stop the system cleanly, press `Ctrl+C` in the terminal before unplugging the power.

---

## Admin Dashboard

Access the dashboard from any browser on the same network:

```
http://<Pi-IP-address>:5000/admin/dashboard
```

Enter the `ADMIN_KEY` from your `.env` file when prompted.

**Dashboard features:**
- Create and manage class sessions (session name, date, start/end time, late threshold)
- Register students (via app or NFC-only)
- Link NFC cards to existing student accounts
- View live attendance roster during class
- Generate session reports and export to CSV
- View full attendance log with filters
- Adjust system config (RSSI threshold, cooldown, duplicate window) without editing code

---

## Database

Local SQLite database (`checkmate_api_test.db`) with four tables:

| Table | Purpose |
|---|---|
| `users` | Student accounts — name, BLE UUID, NFC UID, birthday, device ID |
| `sessions` | Class sessions — date, start/end time, late threshold |
| `attendance` | Logs — user, session, timestamp, method (BLE/NFC/AUTO), status (PRESENT/LATE/ABSENT) |
| `settings` | System config — RSSI threshold, duplicate window, cooldown |

The database is created automatically on first startup.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/users/register` | Register a new student (returns BLE UUID) |
| POST | `/auth/login` | Authenticate and bind device |
| GET | `/attendance/user/<id>` | Get attendance history for a student |
| GET | `/admin/users` | List all users (admin) |
| DELETE | `/admin/users/<id>` | Delete a user (admin) |
| POST | `/admin/sessions` | Create a class session (admin) |
| GET | `/admin/sessions` | List all sessions (admin) |
| GET | `/admin/sessions/<id>/report` | Full class roster with status (admin) |
| DELETE | `/admin/sessions/<id>` | Delete a session (admin) |
| GET | `/admin/attendance` | All attendance logs (admin) |
| GET | `/config` | View system settings (admin) |
| POST | `/config/update` | Update a system setting live (admin) |
| GET | `/admin/nfc/scan` | Arm NFC reader for card enrollment (admin) |
| POST | `/admin/users/create` | Create NFC-only user (admin) |
| POST | `/admin/users/<id>/link-nfc` | Link NFC card to existing user (admin) |

Admin endpoints require an `Admin-Key` header matching the value in `.env`.

---

## Cost

| | |
|---|---|
| Hardware total (excl. VAT) | €127.20 |
| VAT (21%) | €26.71 |
| **Total per unit** | **€153.91** |

---

## UN SDG Alignment

- **SDG 4 — Quality Education:** saves up to 20 hours of instructional time per classroom per semester by eliminating manual roll calls
- **SDG 9 — Industry, Innovation and Infrastructure:** delivers Smart Campus technology for under €160 per unit vs €500–€2,000 for commercial systems
- **SDG 17 — Partnerships for the Goals:** built entirely on open-source libraries with no vendor lock-in

---

## Future Improvements

- Cloud database migration (Firebase / PostgreSQL) for campus-wide deployment
- Multi-classroom support with unique Classroom ID per device
- Advanced anti-spoofing via RSSI triangulation
- Machine learning analytics to flag at-risk attendance patterns
- Integration with school scheduling API for automated session creation

---

## Acknowledgements

Developed as part of the AI Odyssey group project at NHL Stenden University of Applied Sciences, Emmen. Built entirely on open-source tools and libraries.
