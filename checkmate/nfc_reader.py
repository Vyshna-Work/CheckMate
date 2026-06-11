# ============================================================
# MODULE: NFC Reader Module
# PURPOSE: Detects NFC card taps using the PN532 reader,
#          validates the card UID, applies a cooldown to
#          prevent duplicate scans, and fires an event to
#          the Attendance Manager.
#
# HARDWARE: PN532 wired in I2C mode
#   SDA → GPIO2 (physical pin 3)
#   SCL → GPIO3 (physical pin 5)
#   I2C address: 0x24 (set via config.py)
#
# LIBRARY: Uses smbus2 for I2C communication — standard
#          Python 3 library for Raspberry Pi Linux.
#          Install with: pip install smbus2
# ============================================================

import time
import logging
import threading
from typing import Callable, Optional
import smbus2
from smbus2 import i2c_msg

from config import NFC_I2C_ADDRESS, I2C_BUS

logger = logging.getLogger(__name__)

# PN532 command codes (from PN532 user manual)
PN532_CMD_SAMCONFIGURATION    = 0x14   # Set up the Security Access Module
PN532_CMD_INLISTPASSIVETARGET = 0x4A   # Scan for a passive NFC card

# PN532 ACK frame (sent by PN532 after every command to confirm receipt)
PN532_ACK = [0x00, 0x00, 0xFF, 0x00, 0xFF, 0x00]


class NFCReaderModule:
    """
    Handles all NFC card detection for the CheckMate system.

    Uses smbus2 (standard Python 3 I2C library) to communicate
    with the PN532 module over I2C on the Raspberry Pi 4.

    Runs in a polling loop in a background thread. When a valid
    card is tapped, calls on_nfc_detected(uid) to notify the
    Attendance Manager.

    Does NOT look up the student in the database — that is
    the Attendance Manager's job.
    """

    def __init__(
        self,
        on_nfc_detected: Callable[[str], None],
        cooldown_seconds: float = 5.0,
        polling_interval: float = 0.5,
        i2c_bus: int = I2C_BUS,           # from config.py
        i2c_address: int = NFC_I2C_ADDRESS,  # from config.py
    ):
        """
        Args:
            on_nfc_detected:  Callback fired when a valid card is tapped.
                              Receives the UID as a hex string e.g. "04A1B2C3".
                              Connects this module to the Attendance Manager.

            cooldown_seconds: Seconds to ignore the same card after detection.
                              Prevents the same tap being logged twice.

            polling_interval: How often (in seconds) to poll for a card.
                              0.5s means the reader checks every half second.

            i2c_bus:          I2C bus number. Always 1 on Raspberry Pi 4.

            i2c_address:      I2C address of the PN532 (0x24 by default).
                              Change this only if you've rewired the ADDR pin.
        """
        self.on_nfc_detected  = on_nfc_detected
        self.cooldown_seconds = cooldown_seconds
        self.polling_interval = polling_interval
        self.i2c_bus          = i2c_bus
        self.i2c_address      = i2c_address

        # Tracks when each card UID was last seen
        self._last_seen: dict[str, float] = {}

        # Controls the polling loop
        self._running = False

        # smbus2 I2C bus instance — set up in initialise()
        self._bus: Optional[smbus2.SMBus] = None

    # ------------------------------------------------------------------
    # STEP 1 — Hardware Setup
    # ------------------------------------------------------------------

    def initialise(self) -> bool:
        """
        Opens the I2C bus and initialises the PN532 for card reading.
        Must be called before start().

        Returns:
            True  — hardware ready
            False — something went wrong (check wiring or I2C address)
        """
        try:
            # Open the I2C bus
            self._bus = smbus2.SMBus(self.i2c_bus)
            time.sleep(0.1)  # short delay after opening bus

            # Send SAM configuration command to wake up PN532
            # and put it in normal card-reading mode
            self._sam_configuration()

            logger.info(f"PN532 initialised on I2C bus {self.i2c_bus}, address 0x{self.i2c_address:02X}")
            return True

        except Exception as e:
            logger.error(f"PN532 initialisation failed: {e}")
            logger.error("Check: I2C enabled on Pi? Correct wiring? I2C address correct?")
            return False

    def _sam_configuration(self):
        """
        Sends the SAM Configuration command to the PN532.
        This wakes up the chip and sets it to normal operation mode.
        Must be sent before any card reading commands.
        """
        # Command frame: preamble + start code + length + command + data + checksum
        # Mode 0x01 = Normal mode, Timeout = 0x14, IRQ = 0x01
        command = [
            0x00, 0x00, 0xFF,   # Preamble + Start code
            0x05,               # Length (5 bytes of data follow)
            0xFB,               # Length checksum
            0xD4,               # TFI (host to PN532)
            PN532_CMD_SAMCONFIGURATION,
            0x01,               # Normal mode
            0x14,               # Timeout (1 second)
            0x01,               # IRQ enabled
            0x02,               # Data checksum (0x100 - (0xD4+0x14+0x01+0x14+0x01) & 0xFF)
            0x00                # Postamble
        ]
        write = i2c_msg.write(self.i2c_address, command)
        self._bus.i2c_rdwr(write)
        time.sleep(0.1)
        self._read_ack()        # PN532 ACKs every command before responding

    # ------------------------------------------------------------------
    # STEP 2 — Start the Polling Loop
    # ------------------------------------------------------------------

    def start(self) -> None:
        """
        Begins polling for NFC card taps.
        Blocking call — run in a background thread.

        In main.py:
            nfc_thread = threading.Thread(target=nfc_module.start, daemon=True)
            nfc_thread.start()
        """
        if not self._bus:
            logger.error("Cannot start: PN532 not initialised. Call initialise() first.")
            return

        self._running = True
        logger.info("NFC Reader started. Waiting for card taps...")

        while self._running:
            try:
                self._poll_once()
            except Exception as e:
                logger.warning(f"NFC poll error: {e}")

            time.sleep(self.polling_interval)

    def stop(self) -> None:
        """Gracefully stops the polling loop."""
        self._running = False
        if self._bus:
            self._bus.close()
        logger.info("NFC Reader stopped.")

    # ------------------------------------------------------------------
    # STEP 3 — Internal Logic
    # ------------------------------------------------------------------

    def _wait_ready(self, timeout: float = 1.0) -> bool:
        """
        Polls the PN532 until it signals ready (first byte = 0x01).
        Returns True if ready within timeout, False if timed out.
        """
        start = time.time()
        while time.time() - start < timeout:
            try:
                read = i2c_msg.read(self.i2c_address, 1)
                self._bus.i2c_rdwr(read)
                if list(read)[0] == 0x01:
                    return True
            except Exception:
                pass
            time.sleep(0.01)
        return False

    def _read_ack(self) -> bool:
        """
        Reads and verifies the ACK frame the PN532 sends after every command.
        Must be called after every command write, before reading the response.
        Returns True if a valid ACK was received.
        """
        if not self._wait_ready():
            logger.debug("[NFC] Timed out waiting for ACK ready signal")
            return False
        try:
            # ACK frame is 6 bytes, plus 1 leading status byte = 7 total
            read = i2c_msg.read(self.i2c_address, 7)
            self._bus.i2c_rdwr(read)
            ack = list(read)[1:]  # strip status byte
            if ack != PN532_ACK:
                logger.debug(f"[NFC] Bad ACK received: {[hex(b) for b in ack]}")
                return False
            return True
        except Exception as e:
            logger.debug(f"[NFC] ACK read error: {e}")
            return False

    def _poll_once(self) -> None:
        """
        Sends a passive target detection command to the PN532.
        Reads the response and processes any card found.

        Steps:
        1. Send InListPassiveTarget command
        2. Read ACK
        3. Wait for ready
        4. Read response
        5. Parse UID from response
        6. Validate UID length
        7. Check cooldown
        8. Fire event to Attendance Manager
        """
        # Build InListPassiveTarget command
        # MaxTg=1 (detect 1 tag), BrTy=0x00 (106 kbps ISO14443A — MIFARE)
        command = [
            0x00, 0x00, 0xFF,   # Preamble + Start code
            0x04,               # Length
            0xFC,               # Length checksum
            0xD4,               # TFI
            PN532_CMD_INLISTPASSIVETARGET,
            0x01,               # MaxTg — detect 1 tag at a time
            0x00,               # BrTy — 106 kbps ISO14443A
            0xE1,               # Data checksum (0x100 - (0xD4+0x4A+0x01+0x00) & 0xFF)
            0x00                # Postamble
        ]

        try:
            # 1. Send command
            write = i2c_msg.write(self.i2c_address, command)
            self._bus.i2c_rdwr(write)

            # 2. Read ACK — PN532 sends this before the real response
            if not self._read_ack():
                logger.debug("[NFC] No ACK — skipping this poll")
                return

            # 3. Wait until PN532 is ready with the actual response
            if not self._wait_ready():
                logger.debug("[NFC] Timed out waiting for response after ACK")
                return

            # 4. Read the actual card response (up to 30 bytes)
            read = i2c_msg.read(self.i2c_address, 30)
            self._bus.i2c_rdwr(read)
            response = list(read)
            logger.debug(f"[NFC] Raw response: {[hex(b) for b in response]}")
        except Exception as e:
            logger.debug(f"[NFC] Poll I2C error: {e}")
            return  # No card or read error — try again next poll

        # Parse the UID from the response bytes
        uid_bytes = self._parse_uid(response)
        if not uid_bytes:
            return  # No valid card in response

        # Convert bytes to hex string e.g. "04A1B2C3"
        uid_string = self._bytes_to_hex(uid_bytes)

        # Validate UID length (4, 7, or 10 bytes)
        if not self._is_valid_uid(uid_bytes):
            logger.debug(f"Ignoring UID with unexpected length: {uid_string}")
            return

        # Check cooldown — ignore if same card was just tapped
        if self._is_in_cooldown(uid_string):
            logger.debug(f"Ignoring duplicate tap from {uid_string} (cooldown active)")
            return

        # All checks passed — record time and fire event
        self._last_seen[uid_string] = time.time()
        logger.info(f"Valid NFC tap detected: {uid_string}")
        self.on_nfc_detected(uid_string)

    def _parse_uid(self, response: list) -> Optional[bytes]:
        """
        Parses the UID from a raw PN532 InListPassiveTarget response.

        PN532 response structure:
          Byte 0:       I2C status byte (0x01 = ready)
          Byte 1:       Preamble (0x00)
          Bytes 2-3:    Start code (0x00 0xFF)
          Byte 4:       Length
          Byte 5:       Length checksum
          Byte 6:       TFI (0xD5 = PN532 to host)
          Byte 7:       Command code (0x4B)
          Byte 8:       Number of targets found (1 if card present)
          Byte 9:       Target number
          Bytes 10-11:  ATQA
          Byte 12:      SAK
          Byte 13:      UID length
          Bytes 14+:    UID bytes
        """
        try:
            # Full response layout (0-indexed):
            # [0]  = I2C status byte (0x01 = ready)
            # [1]  = 0x00 preamble
            # [2]  = 0x00 start code
            # [3]  = 0xFF start code
            # [4]  = Length
            # [5]  = Length checksum
            # [6]  = TFI (0xD5)
            # [7]  = Command code (0x4B)
            # [8]  = NbTg — number of targets found (0x01 if card present)
            # [9]  = Target number
            # [10] = ATQA byte 0
            # [11] = ATQA byte 1
            # [12] = SAK
            # [13] = UID length
            # [14+]= UID bytes
            if len(response) < 15:
                logger.debug(f"[NFC] Response too short: {len(response)} bytes")
                return None
            if response[8] != 0x01:
                logger.debug(f"[NFC] No card — NbTg={hex(response[8])}")
                return None

            uid_length = response[13]
            uid_bytes  = bytes(response[14:14 + uid_length])

            if len(uid_bytes) != uid_length:
                logger.debug(f"[NFC] UID length mismatch: expected {uid_length}, got {len(uid_bytes)}")
                return None

            return uid_bytes
        except Exception as e:
            logger.debug(f"[NFC] Parse error: {e}")
            return None

    def _is_valid_uid(self, uid_bytes: bytes) -> bool:
        """
        Validates that the UID is one of the standard NFC sizes:
          4 bytes  → MIFARE Classic (most student cards)
          7 bytes  → MIFARE Ultralight / NTAG
          10 bytes → some ISO 14443B cards
        """
        return len(uid_bytes) in (4, 7, 10)

    def _is_in_cooldown(self, uid_string: str) -> bool:
        """
        Returns True if this card was detected too recently.
        Prevents one tap from being logged multiple times.
        """
        last_time = self._last_seen.get(uid_string)
        if last_time is None:
            return False
        return (time.time() - last_time) < self.cooldown_seconds

    @staticmethod
    def _bytes_to_hex(uid_bytes: bytes) -> str:
        """
        Converts raw bytes to an uppercase hex string.
        e.g. b'\\x04\\xa1\\xb2\\xc3' → "04A1B2C3"
        """
        return "".join(f"{b:02X}" for b in uid_bytes)
