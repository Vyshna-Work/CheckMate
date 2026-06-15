# ============================================================
# MODULE: UI Controller
# PURPOSE: Controls the 20x4 LCD display and button input.
#          Shows attendance status, errors, warnings, and
#          the idle scanning screen with live clock.
#          Handles menu navigation via the 4 colour buttons.
#
# LIBRARIES (Python 3 — install on Raspberry Pi):
#   pip install RPLCD RPi.GPIO 
# ============================================================

import threading
from datetime import datetime
import time, random, os

from RPLCD.i2c import CharLCD
import RPi.GPIO as GPIO

from config import (
    LCD_I2C_ADDRESS,
    BTN_UP, BTN_DOWN, BTN_EMPTY, BTN_SELECT,
    RGB_RED, RGB_GREEN, RGB_BLUE,
)

# ─────────────────────────────────────────────────────────
# RGB LED COLOURS  (common cathode — HIGH = on)
# ─────────────────────────────────────────────────────────

LED_OFF    = (0, 0, 0)
LED_GREEN  = (0, 1, 0)   # Present
LED_ORANGE = (1, 1, 0)   # Late  (red + green, no blue)
LED_RED    = (1, 0, 0)   # Error
LED_YELLOW = (1, 1, 0)   # Warning (same as orange at binary output)
LED_BLUE   = (0, 0, 1)   # Idle / scanning


class UIController:
    """
    Controls the 20x4 LCD display and 4 colour buttons.

    Called by the Attendance Manager via:
        ui.show_success(user_name)   — PRESENT check-in
        ui.show_late(user_name)      — LATE check-in
        ui.show_error(message)       — error (unrecognised card etc.)
        ui.show_warning(message)     — warning (already checked in etc.)

    All other display logic (idle screen, menu, animations) is
    handled internally by this module.
    """

    def __init__(self):
        # GPIO setup — must happen before any threads that use GPIO
        GPIO.setmode(GPIO.BCM)

        # Buttons — input with pull-up (active LOW)
        for pin in [BTN_UP, BTN_DOWN, BTN_EMPTY, BTN_SELECT]:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # RGB LED — output (common cathode, HIGH = on)
        for pin in [RGB_RED, RGB_GREEN, RGB_BLUE]:
            GPIO.setup(pin, GPIO.OUT)
        self._set_led(*LED_BLUE)   # idle colour on startup

        # ── LCD init (must be inside __init__ — not at module level) ──
        self.lcd = CharLCD('PCF8574', LCD_I2C_ADDRESS, cols=20, rows=4, charmap='A00')

        self.clear_timer = None
        self.lock = threading.Lock()  # Prevents simultaneous I2C writes
        self.priority_state = False   # True when a status message is showing

        self.current_display_arr = [" " * 20] * 4
        self.old_display_arr = [" " * 20] * 4

        # Menu state
        self.menu_cursor = 0
        self.menu_active = False
        self.menu_arr = [
            "Set Clock",
            "Reboot Device",
            "Close Menu"
        ]

        # Clock thread — starts after GPIO is ready
        self.clock_thread = threading.Thread(target=self._clock, daemon=True)
        self.clock_thread.start()

        # Button polling thread
        self.button_thread = threading.Thread(target=self._buttons, daemon=True)
        self.button_thread.start()

        # self.display_default()

        # Play animated intro on startup
        self.play_intro()

        # self.display_default

    # ------------------------------------------------------------------
    # PUBLIC INTERFACE — called by the Attendance Manager
    # ------------------------------------------------------------------

    def show_success(self, user_name: str):
        """
        Display a success message when attendance is recorded as PRESENT.
        LED → green. Returns to idle (blue) after 4 seconds.
        """
        self._set_led(*LED_GREEN)
        self.display_status("Present", user_name)

    def show_late(self, user_name: str):
        """
        Display a late arrival message when attendance is recorded as LATE.
        LED → orange. Returns to idle (blue) after 4 seconds.
        """
        self._set_led(*LED_ORANGE)
        self.display_status("Late", user_name)

    def show_error(self, message: str):
        """
        Display an error message on the screen.
        LED → red. Returns to idle (blue) after 4 seconds.
        """
        self._set_led(*LED_RED)
        self.display_message("ERROR", message)

    def show_warning(self, message: str):
        """
        Display a warning message on the screen.
        LED → yellow. Returns to idle (blue) after 4 seconds.
        """
        self._set_led(*LED_YELLOW)
        self.display_message("WARNING", message)

    # ------------------------------------------------------------------
    # RGB LED HELPER
    # ------------------------------------------------------------------

    def _set_led(self, r: int, g: int, b: int):
        """
        Sets the RGB LED colour.
        r, g, b are 0 (off) or 1 (on).
        Common cathode — GPIO HIGH turns the channel on.
        """
        GPIO.output(RGB_RED,   GPIO.HIGH if r else GPIO.LOW)
        GPIO.output(RGB_GREEN, GPIO.HIGH if g else GPIO.LOW)
        GPIO.output(RGB_BLUE,  GPIO.HIGH if b else GPIO.LOW)

    # ------------------------------------------------------------------
    # CLEANUP
    # ------------------------------------------------------------------

    def cleanup(self):
        """Releases GPIO pins cleanly. Call this on shutdown."""
        if self.clear_timer:
            self.clear_timer.cancel()
        GPIO.cleanup()

    # ------------------------------------------------------------------
    # BUTTON HANDLING
    # ------------------------------------------------------------------

    def _buttons(self):
        """
        Polls GPIO pins for button presses in a background thread.
        Any button press when idle opens the menu.
        UP/DOWN scroll. SELECT confirms. Menu auto-closes after 10s.
        """
        while True:
            # Any button press opens the menu when idle
            if not self.menu_active:
                if not self.priority_state:
                    for pin in [BTN_UP, BTN_DOWN, BTN_EMPTY, BTN_SELECT]:
                        if GPIO.input(pin) == GPIO.LOW:
                            self.menu_active  = True
                            self.menu_cursor  = 0
                            self.priority_state = True
                            self.display_menu()
                            time.sleep(0.3)  # debounce — prevent re-trigger on same press
                            break

            # Menu is open — handle navigation
            else:
                # UP — scroll cursor up
                if GPIO.input(BTN_UP) == GPIO.LOW:
                    if self.menu_cursor > 0:
                        self.menu_cursor -= 1
                    self.display_menu(False)
                    time.sleep(0.1)

                # DOWN — scroll cursor down
                elif GPIO.input(BTN_DOWN) == GPIO.LOW:
                    if self.menu_cursor < len(self.menu_arr) - 1:
                        self.menu_cursor += 1
                    self.display_menu(False)
                    time.sleep(0.1)

                # SELECT — confirm highlighted option
                elif GPIO.input(BTN_SELECT) == GPIO.LOW:
                    option = self.menu_arr[self.menu_cursor]

                    match option:
                        case "Set Clock":
                            pass  # Placeholder — to be implemented

                        case "Reboot Device":
                            os.system("sudo reboot")

                        case "Close Menu":
                            self.menu_active = False
                            if self.clear_timer:
                                self.clear_timer.cancel()
                            self.display_default()

                    time.sleep(0.1)

            time.sleep(0.05)

    # ------------------------------------------------------------------
    # INTRO ANIMATION
    # ------------------------------------------------------------------

    def play_intro(self):
        """
        Plays the animated startup sequence.
        Wave wipe effect → CheckMate logo → transition to idle.
        """
        INTRO_SLEEP = 0.05
        self.priority_state = True

        # Segment 1: wave cover
        for x in range(-3, 21):
            display_arr = [""] * 4
            string = "░▒▓"
            for y in range(4):
                if x > 0:
                    display_arr[y] = '█' * x
                display_arr[y] += string[:x + 3][::-1]
            self.display(display_arr)
            time.sleep(INTRO_SLEEP)

        # Segment 2: uncover to reveal CheckMate logo
        for x in range(20, -1, -1):
            display_arr = [
                "====================",
                "        CHECK       ",
                "        MATE        ",
                "===================="
            ]
            for y in range(4):
                row_text = (display_arr[y] + " " * (20 - len(display_arr[y])))[:20]
                display_arr[y] = ("█" * x) + row_text[x:]
            self.display(display_arr)
            time.sleep(INTRO_SLEEP)

        time.sleep(1.0)
        self.priority_state = False
        self.display_default()

    # ------------------------------------------------------------------
    # MENU
    # ------------------------------------------------------------------

    def display_menu(self, transition = True):
        """
        Renders the menu with a cursor on the selected option.
        Resets the auto-close timer to 10 seconds on each interaction.
        """
        if self.clear_timer:
            self.clear_timer.cancel()
        self.clear_timer = threading.Timer(10.0, self.display_default)
        self.clear_timer.start()

        menu_arr_display = ["== MAIN MENU =="]
        for option_num in range(len(self.menu_arr)):
            if option_num == self.menu_cursor:
                menu_arr_display.append("> " + self.menu_arr[option_num] + " <")
            else:
                menu_arr_display.append("  " + self.menu_arr[option_num] + "  ")

        if(transition):
            self._transition(menu_arr_display)
        else:
            self.display(menu_arr_display)

    # ------------------------------------------------------------------
    # CLOCK THREAD
    # ------------------------------------------------------------------

    def _clock(self):
        """Updates the time on the idle screen every second."""
        while True:
            if not self.priority_state:
                self.display_default(transition=False)
            time.sleep(0.9)

    # ------------------------------------------------------------------
    # DISPLAY METHODS
    # ------------------------------------------------------------------

    def display(self, display_arr=None):
        """
        Writes a 4-row string array directly to the LCD.
        Each row padded or truncated to exactly 20 characters.
        Thread-safe via lock.
        """
        with self.lock:
            if display_arr is None:
                for row in range(4):
                    self.current_display_arr[row] = (
                        self.current_display_arr[row] + " " * (20 - len(self.current_display_arr[row]))
                    )[:20]
            else:
                for row in range(4):
                    self.current_display_arr[row] = (
                        display_arr[row] + " " * (20 - len(display_arr[row]))
                    )[:20]

            for row in range(4): #old_display_arr
                for col in range(20):
                    if(self.old_display_arr[row][col] != self.current_display_arr[row][col]):
                        self.lcd.cursor_pos = (row, col)
                        self.lcd.write_string(self.current_display_arr[row][col])
            
            self.old_display_arr = self.current_display_arr.copy()

    def display_default(self, transition=True):
        """Shows the idle scanning screen with the current time. LED → blue."""
        self.priority_state = False
        self.menu_active = False
        self._set_led(*LED_BLUE)

        current_time = datetime.now().strftime("%H:%M:%S")
        content = [
            "Status: scanning...",
            "Name: ...",
            f"Time: {current_time}",
            "..."
        ]

        if transition:
            self._transition(content)
        else:
            self.display(content)

    def display_status(self, status: str, name: str):
        """
        Shows the attendance result — status and student name.
        Returns to idle after 4 seconds.
        """
        self.priority_state = True

        if self.clear_timer:
            self.clear_timer.cancel()

        current_time = datetime.now().strftime("%H:%M:%S")
        self._transition([
            f"Status: {status}",
            f"Name:   {name}",
            f"Time:   {current_time}",
            "..."
        ])

        self.clear_timer = threading.Timer(4.0, self.display_default)
        self.clear_timer.start()

    def display_message(self, title: str, message: str):
        """
        Shows a title and message. Used for errors and warnings.
        Returns to idle after 4 seconds.
        """
        self.priority_state = True

        if self.clear_timer:
            self.clear_timer.cancel()

        self._transition([
            f"=== {title} ==="[:20],
            message[:20],
            message[20:40],
            message[40:60]
        ])

        self.clear_timer = threading.Timer(4.0, self.display_default)
        self.clear_timer.start()

    # ------------------------------------------------------------------
    # TRANSITION ANIMATION
    # ------------------------------------------------------------------

    def _transition(self, _end_state):
        """
        Animates characters sliding from their current LCD positions
        to their new positions when the screen content changes.

        How it works:
          1. Build a list of every non-space character the new screen needs.
          2. Reuse characters already on screen where possible (same letter),
             converting case or substituting if needed — so characters appear
             to morph and slide rather than vanishing and reappearing.
          3. Blank out any character whose start and end positions are the same
             (no movement needed).
          4. Each frame: move every character one step closer to its target,
             redraw, sleep. Repeat until all characters have reached their
             target positions.
        """
        
        # self.priority_state = True

        ANIM_SLEEP = 0.01

        start_state = self.current_display_arr.copy()
        end_state   = _end_state.copy()

        # Pad all rows to 20 characters so indexing is always safe
        for y in range(4):
            start_state[y] = (start_state[y] + ' ' * (20 - len(start_state[y])))[:20]
            end_state[y]   = (end_state[y]   + ' ' * (20 - len(end_state[y])))[:20]

        # Build the list of characters the end screen needs (excluding spaces)
        needed_arr = []
        for y in range(4):
            for x in range(20):
                if end_state[y][x] != ' ':
                    needed_arr.append(end_state[y][x])

        # Try to reuse characters already on screen.
        # For each non-space character currently on screen, check if the
        # destination needs the same letter (exact, lowercase, or uppercase).
        # If yes, mark it as claimed. If not, replace it with a needed character.
        # This way existing characters slide to their new homes instead of blinking.
        for y in range(4):
            for x in range(20):
                if len(needed_arr) > 0:
                    if start_state[y][x] != ' ':
                        if start_state[y][x] in needed_arr:
                            needed_arr.remove(start_state[y][x])
                        elif start_state[y][x].lower() in needed_arr:
                            start_state[y] = start_state[y][:x] + start_state[y][x].lower() + start_state[y][x+1:]
                            needed_arr.remove(start_state[y][x])
                        elif start_state[y][x].upper() in needed_arr:
                            start_state[y] = start_state[y][:x] + start_state[y][x].upper() + start_state[y][x+1:]
                            needed_arr.remove(start_state[y][x])
                        else:
                            # No match — swap in a needed character at this position
                            char = random.choice(needed_arr)
                            start_state[y] = start_state[y][:x] + char + start_state[y][x+1:]
                            needed_arr.remove(char)

        # Blank out positions that are already correct — no animation needed there
        for y in range(4):
            for x in range(20):
                if start_state[y][x] == end_state[y][x]:
                    start_state[y] = start_state[y][:x] + ' ' + start_state[y][x+1:]

        self.display(start_state)

        # Convert each character into a movement object:
        # [char, current_x, current_y, target_x, target_y]
        current_char_arr = [
            (start_state[y][x], x, y)
            for y in range(4) for x in range(20)
            if start_state[y][x] != ' '
        ]
        end_char_arr = [
            (end_state[y][x], x, y)
            for y in range(4) for x in range(20)
            if end_state[y][x] != ' '
        ]

        # Pair each current character with its matching target position.
        # First-come first-served: once a target slot is claimed, skip it.
        char_mov_arr = []
        marked = []
        for cur_char in current_char_arr:
            for end_char in end_char_arr:
                if end_char in marked:
                    continue
                if cur_char[0] == end_char[0]:
                    marked.append(end_char)
                    char_mov_arr.append([cur_char[0], cur_char[1], cur_char[2], end_char[1], end_char[2]])
                    break

        # Any target position not yet claimed spawns from a random existing char
        for end_char in end_char_arr:
            if end_char not in marked:
                rand_char = random.choice(char_mov_arr) if char_mov_arr else [' ', 0, 0, 0, 0]
                char_mov_arr.append([end_char[0], rand_char[1], rand_char[2], end_char[1], end_char[2]])

        # Each frame: step every character one pixel closer to its target.
        # char format: [character, current_x, current_y, target_x, target_y]
        change = True
        frame_num = 0
        while change:
            change = False
            state = [" " * 20] * 4

            for char in char_mov_arr:
                # Move one step horizontally toward target
                if char[1] > char[3]:
                    char[1] -= 1; change = True
                elif char[1] < char[3]:
                    char[1] += 1; change = True

                # Move one step vertically toward target
                if char[2] > char[4]:
                    char[2] -= 1; change = True
                elif char[2] < char[4]:
                    char[2] += 1; change = True

                # Write character at its current position in this frame
                state[char[2]] = state[char[2]][:char[1]] + char[0] + state[char[2]][char[1]+1:]

            self.display(state)

            time.sleep(ANIM_SLEEP)

            frame_num += 1

        # Snap to final state to make sure everything is pixel-perfect
        self.display(end_state)
        # self.priority_state = False
