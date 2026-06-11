# ============================================================
# MODULE: BLE Scanner Module
# PURPOSE: Continuously scans for iBeacon BLE advertisements
#          broadcast by the CheckMate Android app.
#          Extracts the Proximity UUID from the iBeacon payload,
#          applies RSSI and cooldown filters, and forwards valid
#          detections to the Attendance Manager.
#
# iBeacon FORMAT (inside manufacturer data):
#   Bytes 0-1  : Company ID       → 0x004C (Apple, used by iBeacon standard)
#   Byte  2    : iBeacon type     → 0x02
#   Byte  3    : iBeacon length   → 0x15 (21 bytes follow)
#   Bytes 4-19 : Proximity UUID   → 16 bytes (the student's unique BLE ID)
#   Bytes 20-21: Major value      → 2 bytes (not used for identification)
#   Bytes 22-23: Minor value      → 2 bytes (not used for identification)
#   Byte  24   : TX Power         → 1 byte  (not used)
# ============================================================

import asyncio
import logging
import time
from typing import Callable, Optional
from uuid import UUID

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from config import RSSI_THRESHOLD, DETECTION_COOLDOWN, runtime_config

logger = logging.getLogger(__name__)

# iBeacon constants
IBEACON_COMPANY_ID = 0x004C   # Apple company ID used by iBeacon standard
IBEACON_TYPE       = 0x02     # iBeacon type identifier byte
IBEACON_LENGTH     = 0x15     # Expected payload length (21 bytes)


class BLEScannerModule:
    """
    Scans for iBeacon BLE advertisements from the CheckMate Android app.

    Each registered student's app broadcasts an iBeacon with their unique
    Proximity UUID (assigned at registration by the API). This module
    reads that UUID and passes it to the Attendance Manager for lookup.

    All non-iBeacon devices and iBeacons with unrecognised UUIDs are
    silently ignored.
    """

    def __init__(
        self,
        on_ble_detected: Callable[[str, int], None],
        rssi_threshold: int = RSSI_THRESHOLD,
        detection_cooldown: int = DETECTION_COOLDOWN,
    ):
        """
        Args:
            on_ble_detected:    Callback fired when a valid student iBeacon
                                is detected. Receives (proximity_uuid, rssi).
                                Connects the BLE Scanner to the Attendance Manager.

            rssi_threshold:     Minimum signal strength in dBm.
                                Devices weaker than this are too far away.

            detection_cooldown: Seconds before the same UUID triggers again.
                                Prevents logging the same student repeatedly
                                while they sit near the reader.
        """
        self.on_ble_detected    = on_ble_detected
        self.rssi_threshold     = rssi_threshold
        self.detection_cooldown = detection_cooldown

        # Tracks when each UUID was last detected
        # Format: { "550e8400-e29b-41d4-a716-446655440000": 1718000000.0 }
        self._last_seen: dict[str, float] = {}

        # Controls whether the scan loop is running
        self._running = False

        # The BleakScanner instance
        self._scanner: Optional[BleakScanner] = None

    # ------------------------------------------------------------------
    # START / STOP
    # ------------------------------------------------------------------

    def start(self):
        """
        Starts the BLE scanning loop.
        Blocking call — run in a background thread.

        In main.py:
            ble_thread = threading.Thread(target=ble_module.start, daemon=True)
            ble_thread.start()
        """
        self._running = True
        logger.info("BLE Scanner starting (iBeacon mode)...")

        # Create a fresh asyncio event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._scan_loop())
        except Exception as e:
            logger.error(f"BLE Scanner error: {e}")
        finally:
            loop.close()

    def stop(self):
        """Signals the scan loop to stop gracefully."""
        self._running = False
        logger.info("BLE Scanner stopping...")

    # ------------------------------------------------------------------
    # SCAN LOOP
    # ------------------------------------------------------------------

    async def _scan_loop(self):
        """
        Main async scanning loop.
        Runs the BleakScanner continuously until stop() is called.
        """
        self._scanner = BleakScanner(detection_callback=self._detection_callback)

        await self._scanner.start()
        logger.info("BLE Scanner active. Listening for iBeacon advertisements...")

        while self._running:
            await asyncio.sleep(1)

        await self._scanner.stop()
        logger.info("BLE Scanner stopped.")

    # ------------------------------------------------------------------
    # DETECTION CALLBACK
    # Called by Bleak for every BLE advertisement received
    # ------------------------------------------------------------------

    async def _detection_callback(
        self,
        device: BLEDevice,
        advertisement_data: AdvertisementData
    ):
        """
        Called automatically by Bleak for every nearby BLE advertisement.

        Steps:
        1. Check manufacturer data exists
        2. Check it matches iBeacon format (company ID + type + length)
        3. Extract the 16-byte Proximity UUID
        4. Check RSSI threshold
        5. Check cooldown
        6. Forward UUID to Attendance Manager
        """

        # ── Step 1: Check manufacturer data exists ───────
        # iBeacon data is embedded in the manufacturer data field.
        # If there's no manufacturer data, it's not an iBeacon — ignore.
        manufacturer_data = advertisement_data.manufacturer_data
        if not manufacturer_data:
            return

        # ── Step 2: Check iBeacon format ─────────────────
        # iBeacon uses Apple's company ID (0x004C).
        # If this company ID isn't present, it's not an iBeacon.
        ibeacon_payload = manufacturer_data.get(IBEACON_COMPANY_ID)
        if not ibeacon_payload:
            return

        # Verify the payload is the right length (23 bytes minimum)
        # and matches the iBeacon type (0x02) and length (0x15) bytes
        if len(ibeacon_payload) < 23:
            return

        if ibeacon_payload[0] != IBEACON_TYPE or ibeacon_payload[1] != IBEACON_LENGTH:
            return

        # ── Step 3: Extract the Proximity UUID ───────────
        # Bytes 2–17 (16 bytes) are the Proximity UUID.
        # This is the student's unique BLE ID stored in the database.
        proximity_uuid = self._extract_uuid(ibeacon_payload[2:18])
        if not proximity_uuid:
            return

        # ── Step 4: RSSI threshold check ─────────────────
        # Ignore devices that are too far away.
        rssi = advertisement_data.rssi
        if rssi is None or rssi < runtime_config["rssi_threshold"]:
            logger.debug(f"[BLE] iBeacon {proximity_uuid} too weak (RSSI: {rssi}), ignoring.")
            return

        # ── Step 5: Cooldown check ────────────────────────
        # Ignore same UUID if detected recently.
        if self._is_in_cooldown(proximity_uuid):
            logger.debug(f"[BLE] iBeacon {proximity_uuid} in cooldown, ignoring.")
            return

        # ── Step 6: All checks passed — forward to Attendance Manager ──
        self._last_seen[proximity_uuid] = time.time()

        logger.info(f"[BLE] Valid iBeacon detected — UUID: {proximity_uuid}, RSSI: {rssi}")

        # Fire the event to the Attendance Manager
        # proximity_uuid matches ble_id in the database
        self.on_ble_detected(proximity_uuid, rssi)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _extract_uuid(self, uuid_bytes: bytes) -> Optional[str]:
        """
        Converts 16 raw bytes into a standard UUID string.

        iBeacon stores the UUID in big-endian byte order.

        Example:
            b'\\x55\\x0e\\x84\\x00...'
            → "550e8400-e29b-41d4-a716-446655440000"

        Returns None if the bytes cannot be parsed as a valid UUID.
        """
        try:
            return str(UUID(bytes=uuid_bytes))
        except Exception:
            logger.debug(f"[BLE] Could not parse UUID bytes: {uuid_bytes.hex()}")
            return None

    def _is_in_cooldown(self, proximity_uuid: str) -> bool:
        """
        Returns True if this UUID was detected recently
        and is still within the cooldown period.
        """
        last_time = self._last_seen.get(proximity_uuid)
        if last_time is None:
            return False
        return (time.time() - last_time) < self.detection_cooldown
