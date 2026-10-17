# Eye Spy dock firmware (MicroPython on an ESP32 DevKit V1).
#
# What it does:
#   * polls GET /device/status every 15 s; when a dose is due: red LED + beeps
#   * watches the lift switch under the bottle cup; posts "lifted" / "returned"
#   * the big button silences the alarm for the current dose
#
# MicroPython runs main.py automatically at boot. Wiring: see hardware/README.md.

import time

import network
import requests  # bundled with MicroPython >= 1.20 (older builds: "import urequests as requests")
from machine import PWM, Pin

import config

# ---- Pins ------------------------------------------------------------------
led_green = Pin(25, Pin.OUT)            # waiting / all good
led_red = Pin(26, Pin.OUT)              # dose due (blinks slowly when offline)
buzzer = PWM(Pin(27), freq=880, duty_u16=0)
lift_switch = Pin(14, Pin.IN, Pin.PULL_UP)    # to GND; 0 = bottle is in the cup
silence_button = Pin(33, Pin.IN, Pin.PULL_UP)  # to GND

# ---- Timing (ms) -------------------------------------------------------------
POLL_MS = 15000          # status poll interval
DEBOUNCE_MS = 50
LIFT_CONFIRM_MS = 1500   # bottle must be out this long to count (ignores bumps)
BEEP_EVERY_MS = 20000    # alarm repeat while a dose is due
QUEUE_MAX = 16

HEADERS = {"X-Device-Token": config.DEVICE_TOKEN}


class Dock:
    def __init__(self):
        self.dose_due = False
        self.due_dose_id = None
        self.silenced_dose_id = None
        self.last_poll = None
        self.last_beep = None

        present = lift_switch.value() == 0
        self.bottle_present = present   # debounced state
        self.raw_present = present
        self.raw_changed_at = time.ticks_ms()
        self.lift_started_at = 0
        self.lift_reported = False
        self.last_silence = 1

        # (event, ticks_ms) waiting for the backend; survives short WiFi drops.
        self.queue = []

    # ---- Network -------------------------------------------------------------
    def poll_status(self):
        try:
            r = requests.get(config.BACKEND_URL + "/device/status", headers=HEADERS, timeout=5)
            if r.status_code == 200:
                body = r.json()
                self.dose_due = bool(body.get("dose_due"))
                self.due_dose_id = body.get("dose_id")
            else:
                print("status failed:", r.status_code)
            r.close()
        except Exception as exc:
            print("status error:", exc)

    def send_event(self, event, at_ms):
        # age_ms lets the backend timestamp the event without the dock needing a real clock.
        age = time.ticks_diff(time.ticks_ms(), at_ms)
        try:
            r = requests.post(
                config.BACKEND_URL + "/device/events",
                json={"event": event, "age_ms": age},
                headers=HEADERS,
                timeout=5,
            )
            ok = r.status_code in (200, 422)  # 422 = malformed; drop instead of retrying forever
            print("event", event, "->", r.status_code)
            r.close()
            return ok
        except Exception as exc:
            print("event error:", exc)
            return False

    def enqueue(self, event, at_ms):
        if len(self.queue) >= QUEUE_MAX:
            self.queue.pop(0)  # full: drop the oldest
        self.queue.append((event, at_ms))

    def flush_queue(self):
        while self.queue and self.send_event(*self.queue[0]):
            self.queue.pop(0)
            self.last_poll = None  # poll right away so the LEDs update

    # ---- Inputs --------------------------------------------------------------
    def read_lift_switch(self):
        now = time.ticks_ms()
        present = lift_switch.value() == 0
        if present != self.raw_present:
            self.raw_present = present
            self.raw_changed_at = now

        # Accept a change only once the switch has been stable for DEBOUNCE_MS.
        if self.raw_present != self.bottle_present and time.ticks_diff(now, self.raw_changed_at) >= DEBOUNCE_MS:
            self.bottle_present = self.raw_present
            if not self.bottle_present:
                self.lift_started_at = self.raw_changed_at
                self.lift_reported = False
            elif self.lift_reported:
                self.enqueue("returned", self.raw_changed_at)
            # else: a short bump, ignored

        # A lift counts once the bottle has been out for LIFT_CONFIRM_MS.
        if (not self.bottle_present and not self.lift_reported
                and time.ticks_diff(now, self.lift_started_at) >= LIFT_CONFIRM_MS):
            self.enqueue("lifted", self.lift_started_at)
            self.lift_reported = True
            self.silenced_dose_id = self.due_dose_id  # they're taking it: stop beeping

    def read_silence_button(self):
        value = silence_button.value()
        if self.last_silence == 1 and value == 0 and self.dose_due:
            self.silenced_dose_id = self.due_dose_id
            buzzer.duty_u16(0)
        self.last_silence = value

    # ---- Outputs -------------------------------------------------------------
    def beep(self):
        for _ in range(3):
            buzzer.duty_u16(32768)
            time.sleep_ms(180)
            buzzer.duty_u16(0)
            time.sleep_ms(80)

    def update_outputs(self, online):
        now = time.ticks_ms()
        if not online:
            led_green.value(0)
            led_red.value((now // 1000) % 2)  # slow blink = no connection
            return
        led_green.value(0 if self.dose_due else 1)
        led_red.value(1 if self.dose_due else 0)

        alarm_on = self.dose_due and self.due_dose_id != self.silenced_dose_id and self.bottle_present
        if alarm_on and (self.last_beep is None or time.ticks_diff(now, self.last_beep) >= BEEP_EVERY_MS):
            self.beep()
            self.last_beep = now
        if not self.dose_due:
            self.last_beep = None


def connect_wifi(wlan, last_try):
    """Starts a connection attempt at most every 10 s. Returns the time of the last attempt."""
    now = time.ticks_ms()
    if wlan.isconnected():
        return last_try
    if last_try is None or time.ticks_diff(now, last_try) >= 10000:
        print("Connecting to WiFi...")
        try:
            wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        except OSError as exc:  # raised if a previous attempt is still in progress
            print("wifi error:", exc)
        return now
    return last_try


def main():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    dock = Dock()
    last_wifi_try = None

    while True:
        last_wifi_try = connect_wifi(wlan, last_wifi_try)
        dock.read_lift_switch()
        dock.read_silence_button()

        online = wlan.isconnected()
        if online:
            dock.flush_queue()
            if dock.last_poll is None or time.ticks_diff(time.ticks_ms(), dock.last_poll) >= POLL_MS:
                dock.poll_status()
                dock.last_poll = time.ticks_ms()
        dock.update_outputs(online)
        time.sleep_ms(10)


main()
