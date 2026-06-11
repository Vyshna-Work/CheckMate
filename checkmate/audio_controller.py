# ============================================================
# MODULE: Audio Controller
# PURPOSE: Provides immediate audio feedback during the
#          attendance process by playing predefined sound
#          cues for success, errors, warnings, and
#          personalised student greetings.
#
#          Runs audio playback in a background thread so it
#          never blocks the rest of the system (BLE scanning,
#          NFC polling, API server).
# ============================================================

import os
import platform
import threading
import logging
import time
import random

logger = logging.getLogger(__name__)


class AudioController:
    """
    Manages all audio output for the CheckMate system.

    Plays personalised voice greetings for students on arrival,
    late arrival notifications, and system feedback tones for
    errors and warnings.

    All playback is non-blocking — audio runs in its own thread
    so the Attendance Manager can continue processing immediately.
    """

    def __init__(self, sounds_folder: str = "sounds", enabled: bool = True):
        """
        Args:
            sounds_folder:  Path to the folder containing all audio files.
                            Defaults to a 'sounds' subfolder in the project.

            enabled:        Set to False to disable all audio output.
                            Useful for testing without a speaker connected.
        """
        self.sounds_folder = sounds_folder
        self.enabled       = enabled

        # ── Sound file map ────────────────────────────────
        # Maps sound names to their filenames.
        # Personalised greetings are keyed by student name.
        # System sounds are keyed by event type.
        self.sounds = {
            # Personalised arrival greetings
            "arrival_salman":   "arrival_salman.m4a",
            "arrival_sjonly":   "arrival_sjonly.m4a",

            "personal_arrival_uraib":          "1.uraib.m4a",
            "personal_late_uraib":          "2.uraib.m4a",

            "iris_late":        "iris_late.m4a",
            "miguel_late":      "miguel_late.m4a",
            "jacquline_late":   "jacquline_late.m4a",
            "marcel_late":      "marcel_late.m4a",

            "birthday":         "birthday.m4a",

            # Generic system sounds
            "arrival_generic":          "arrival.m4a",    # generic success / present
            "invalid":          "invalid.m4a",    # error / unrecognised card or device
            "generic_late":             "iris_late.m4a",  # generic late arrival fallback
            "warning":          "invalid.m4a",    # warning (e.g. already checked in)
        }

    # ------------------------------------------------------------------
    # PUBLIC INTERFACE
    # Called by the Attendance Manager
    # ------------------------------------------------------------------

    def play_success(self, user_name: str = "404"):
        """
        Play a success sound when attendance is recorded as PRESENT.

        If a personalised greeting exists for the user, it plays that.
        Otherwise falls back to the generic arrival sound.

        Args:
            user_name: The student's name (as stored in the database).
                       Used to look up a personalised greeting.
        """
        # if user_name:
        # Build a lookup key from the name e.g. "Salman" → "arrival_salman"
        personalised_key = f"personal_arrival_{user_name.lower().strip()}"
        if personalised_key in self.sounds:
            self._play_async(personalised_key)
            return
        else:
            arrival_sounds = []
            for key in self.sounds:
                if(("arrival_" in key) and (not("personal_" in key))):
                    arrival_sounds.append(key)

            personalised_key = random.choice(arrival_sounds)
            self._play_async(personalised_key)
            return

        # No personalised greeting found — play generic arrival sound
        # self._play_async("arrival")

    def play_late(self, user_name: str = "404"):
        """
        Play a late arrival sound when attendance is recorded as LATE.

        If a personalised late greeting exists, it plays that.
        Otherwise falls back to the generic late sound.

        Args:
            user_name: The student's name for personalised late greeting lookup.
        """
        personalised_key = f"personal_late_{user_name.lower().strip()}"
        if personalised_key in self.sounds:
            self._play_async(personalised_key)
            return
        else:
            late_sounds = []
            for key in self.sounds:
                if(("late" in key) and (not("personal" in key))):
                    late_sounds.append(key)

            personalised_key = random.choice(late_sounds)
            if personalised_key in self.sounds:
                self._play_async(personalised_key)
                return

        # if user_name:
        #     personalised_key = f"{user_name.lower().strip()}_late"
        #     if personalised_key in self.sounds:
        #         self._play_async(personalised_key)
        #         return

        # No personalised late sound — play generic late sound
        # self._play_async("late")

    def play_error(self):
        """
        Play an error sound for unrecognised cards or devices.
        """
        self._play_async("invalid")

    def play_warning(self):
        """
        Play a warning sound e.g. when a student is already checked in.
        """
        self._play_async("warning")

    def play_birthday(self, user_name: str = None, delay: float = 8.0):
        """
        Play the birthday sound if today is the student's birthday.
        Called by the Attendance Manager after checking the user's birthday field.

        Args:
            delay: Seconds to wait before playing, so the arrival greeting
                   finishes first. Defaults to 3 seconds.
        """
        def _delayed():
            time.sleep(delay)
            self._play_sound("birthday")

        if not self.enabled:
            return

        thread = threading.Thread(target=_delayed, daemon=True, name="Audio-birthday")
        thread.start()

    def play(self, sound_name: str):
        """
        Play any sound by name directly.
        Useful for custom or one-off sounds.

        Args:
            sound_name: Key from the sounds dictionary.
        """
        self._play_async(sound_name)

    # ------------------------------------------------------------------
    # INTERNAL — Non-blocking playback
    # ------------------------------------------------------------------

    def _play_async(self, sound_name: str):
        """
        Plays a sound in a background thread so it never blocks
        the Attendance Manager or any other module.
        """
        if not self.enabled:
            logger.debug(f"[AUDIO] Audio disabled — skipping: {sound_name}")
            return

        # Run playback in a daemon thread
        thread = threading.Thread(
            target=self._play_sound,
            args=(sound_name,),
            daemon=True,
            name=f"Audio-{sound_name}"
        )
        thread.start()

    def _play_sound(self, sound_name: str):
        """
        Resolves the sound name to a file path and plays it.
        Detects the operating system to use the correct playback command.
        """
        filename = self.sounds.get(sound_name)

        if not filename:
            logger.warning(f"[AUDIO] Sound not found: '{sound_name}'")
            return

        # Build the full path to the audio file
        filepath = os.path.join(self.sounds_folder, filename)

        if not os.path.exists(filepath):
            logger.warning(f"[AUDIO] File not found: {filepath}")
            return

        logger.info(f"[AUDIO] Playing: {filepath}")
        self._play_audio(filepath)

    def _play_audio(self, filepath: str):
        """
        Plays an audio file using the appropriate system command.

        - Windows : uses the default media player via 'start'
        - macOS   : uses 'open' (for testing on a Mac)
        - Linux   : uses ffplay (the correct command for Raspberry Pi)
                    ffplay is part of ffmpeg — install with:
                    sudo apt install ffmpeg
        """
        system = platform.system()

        try:
            if system == "Windows":
                os.system(f'start "" "{filepath}"')
            elif system == "Darwin":
                os.system(f'afplay "{filepath}"')
            else:
                # Raspberry Pi / Linux — PAM8402 amplifier via GPIO18 PWM audio.
                # Requires /boot/config.txt to have: dtoverlay=audremap,pins_18_19
                # -autoexit      : close ffplay when audio finishes
                # -nodisp        : no video window (audio only)
                # -loglevel quiet: suppress ffplay terminal output
                # -af volume=2   : boost volume (adjust 2.0 to taste)
                os.system(f'ffplay -autoexit -nodisp -loglevel quiet -af volume=2 "{filepath}"')
        except Exception as e:
            logger.error(f"[AUDIO] Playback error: {e}")
