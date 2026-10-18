from machine import Pin, SoftI2C
import time
import network

try:
    import requests  # bundled with MicroPython >= 1.20
except ImportError:
    import urequests as requests

# WiFi + backend settings. Without config.py the dock runs the offline demo.
try:
    import config
except ImportError:
    config = None

# ==========================================
# HARDWARE PIN CONFIGURATION
# ==========================================
PIN_SWITCH = 13   # Micro Switch signal pin (D13)
PIN_RED    = 25   # Red LED pin (D25)
PIN_GREEN  = 26   # Green LED pin (D26)
PIN_SDA    = 21   # LCD I2C SDA (D21)
PIN_SCL    = 22   # LCD I2C SCL (D22)

# ==========================================
# TIMING & MEDICAL SCHEDULE CONFIGURATION
# ==========================================
# Safety waiting interval between drops (in seconds)
WAIT_BETWEEN_DROPS = 20  # Set to 20 for demo, 300 for 5 minutes

# Standby time before next dose alarm triggers (in seconds for demo)
TIME_UNTIL_NEXT_DOSE = 10  # Seconds to wait in standby before alarm

# Doctor's prescribed schedule list (offline demo only; online, the backend has the schedule)
DOCTOR_SCHEDULE = ["08:00 AM", "02:00 PM", "08:00 PM"]

# ==========================================
# BACKEND CONFIGURATION (online mode)
# ==========================================
POLL_SECONDS = 15       # How often to ask the backend whether a dose is due
RECHECK_SECONDS = 60    # While alarming, how often to check the dose is still due
WIFI_TIMEOUT = 15       # Seconds to wait for WiFi before showing "No connection"
QUEUE_MAX = 16          # Drops kept while offline, sent when the connection returns

# Initialize GPIO Pins
switch = Pin(PIN_SWITCH, Pin.IN, Pin.PULL_UP)
led_red = Pin(PIN_RED, Pin.OUT)
led_green = Pin(PIN_GREEN, Pin.OUT)

# ==========================================
# EMBEDDED LCD1602 I2C DRIVER (PCF8574)
# ==========================================
class LCD1602:
    def __init__(self, sda_pin, scl_pin):
        self.i2c = SoftI2C(scl=Pin(scl_pin), sda=Pin(sda_pin), freq=100000)
        self.addr = None
        self.shown = None
        for a in [0x27, 0x3F]:
            try:
                if a in self.i2c.scan():
                    self.addr = a
                    break
            except Exception:
                pass
        if self.addr:
            self._init_lcd()
            print(f"[LCD] Connected at {hex(self.addr)}")
        else:
            print("[LCD] Device not found on I2C bus. Outputting to console.")

    def _write_byte(self, data):
        if self.addr:
            try:
                self.i2c.writeto(self.addr, bytes([data | 0x08]))
            except Exception:
                pass

    def _send_nibble(self, nibble, mode):
        val = (nibble << 4) | mode
        self._write_byte(val | 0x04)
        time.sleep_us(500)
        self._write_byte(val & ~0x04)
        time.sleep_us(500)

    def _send_byte(self, val, mode):
        self._send_nibble(val >> 4, mode)
        self._send_nibble(val & 0x0F, mode)

    def _init_lcd(self):
        time.sleep_ms(50)
        for _ in range(3):
            self._send_nibble(0x03, 0)
            time.sleep_ms(5)
        self._send_nibble(0x02, 0)
        self._send_byte(0x28, 0)
        self._send_byte(0x0C, 0)
        self._send_byte(0x06, 0)
        self.clear()

    def clear(self):
        self._send_byte(0x01, 0)
        time.sleep_ms(2)

    def display(self, line1, line2=""):
        self.shown = (line1, line2)
        print(f"\n[LCD] --------------------")
        print(f"| {line1:<16} |")
        print(f"| {line2:<16} |")
        print(f"--------------------------")
        if not self.addr:
            return
        self.clear()
        self._send_byte(0x80, 0)
        for char in line1[:16]:
            self._send_byte(ord(char), 1)
        if line2:
            self._send_byte(0xC0, 0)
            for char in line2[:16]:
                self._send_byte(ord(char), 1)

    def show(self, line1, line2=""):
        """Like display(), but skips redrawing (and flicker) when the text hasn't changed."""
        if self.shown != (line1, line2):
            self.display(line1, line2)

lcd = LCD1602(PIN_SDA, PIN_SCL)

def wait_for_switch_press():
    """Wait for patient to press the micro switch to confirm a dose."""
    while switch.value() == 1:
        time.sleep_ms(50)
    while switch.value() == 0:
        time.sleep_ms(50)
    time.sleep_ms(200)

def countdown_between_drops(title):
    """Red LED on while the LCD counts down the safe wait before the next drop."""
    led_red.value(1)    # Red LED ON: absorption wait active
    led_green.value(0)
    print("\n[INTERVAL] Drop confirmed. Starting safety countdown...")

    for remaining in range(WAIT_BETWEEN_DROPS, 0, -1):
        mins = remaining // 60
        secs = remaining % 60
        lcd.display(title, "Wait: {:02d}:{:02d} min".format(mins, secs))
        time.sleep(1)

    led_red.value(0)    # Red LED OFF

# ==========================================
# BACKEND CONNECTION (online mode)
# ==========================================
wlan = None
pending_drops = []  # ticks_ms of drops not yet sent to the backend

def connect_wifi():
    """Connect (or stay connected) to WiFi. Returns True when connected."""
    global wlan
    if wlan is None:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
    if wlan.isconnected():
        return True
    print("[WIFI] Connecting to", config.WIFI_SSID)
    lcd.show("Connecting WiFi", config.WIFI_SSID[:16])
    try:
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    except OSError as exc:  # raised if a previous attempt is still in progress
        print("[WIFI] error:", exc)
    start = time.ticks_ms()
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < WIFI_TIMEOUT * 1000:
        time.sleep_ms(250)
    if wlan.isconnected():
        print("[WIFI] Connected, IP", wlan.ifconfig()[0])
    return wlan.isconnected()

def get_status():
    """Ask the backend whether a dose is due. Returns the JSON body, or None when unreachable."""
    if not connect_wifi():
        return None
    try:
        r = requests.get(config.BACKEND_URL + "/device/status",
                         headers={"X-Device-Token": config.DEVICE_TOKEN}, timeout=5)
        body = r.json() if r.status_code == 200 else None
        if body is None:
            print("[NET] status failed:", r.status_code)
        r.close()
        return body
    except Exception as exc:
        print("[NET] status error:", exc)
        return None

def send_drop(pressed_at):
    """Post one drop as a bottle "lifted" event. Returns (done, flag).

    age_ms tells the backend how long ago the drop happened, so drops sent late
    (after a WiFi drop) still get the right time. done=False means retry later.
    """
    age = time.ticks_diff(time.ticks_ms(), pressed_at)
    try:
        r = requests.post(config.BACKEND_URL + "/device/events",
                          json={"event": "lifted", "age_ms": age},
                          headers={"X-Device-Token": config.DEVICE_TOKEN}, timeout=5)
        status = r.status_code
        flag = r.json().get("flag") if status == 200 else None
        r.close()
    except Exception as exc:
        print("[NET] event error:", exc)
        return False, None
    print("[NET] drop sent ->", status, flag)
    if status == 401:
        print("[NET] Dock not registered: run python -m scripts.register_device on the backend")
    # 4xx won't succeed on retry (bad token, too old), so drop it; retry network and 5xx errors.
    return status < 500, flag

def log_drop(pressed_at):
    """Queue a drop and send everything queued. Returns the backend's flag for it, or None if queued."""
    if len(pending_drops) >= QUEUE_MAX:
        pending_drops.pop(0)  # full: drop the oldest
    pending_drops.append(pressed_at)
    return flush_drops()

def flush_drops():
    flag = None
    while pending_drops:
        done, flag = send_drop(pending_drops[0])
        if not done:
            return None
        pending_drops.pop(0)
    return flag

EYE_TEXT = {"left": "left eye", "right": "right eye", "both": "both eyes"}
FLAG_TEXT = {"on_time": "Logged: on time", "late": "Logged: late",
             "early": "Logged: early", "too_frequent": "Logged: extra"}

def dose_text(status):
    """Second LCD line for a due dose, e.g. "1 drop, left eye"."""
    n = status.get("drops") or 1
    eye = EYE_TEXT.get(status.get("eye"), "eye")
    text = "{} drop{}, {}".format(n, "" if n == 1 else "s", eye)
    return text if len(text) <= 16 else "{}x {}".format(n, eye)

def wait_for_drop(status):
    """Alarm screens until the switch is pressed. Returns the press time (ticks_ms),
    or None if the dose stopped being due (missed, or taken another way)."""
    screens = [("Time to take", "your eye drops!"),
               ((status.get("medication") or "Eye drop")[:16], dose_text(status))]
    started = last_check = time.ticks_ms()
    while switch.value() == 1:
        now = time.ticks_ms()
        lcd.show(*screens[(time.ticks_diff(now, started) // 3000) % 2])  # alternate every 3 s
        if time.ticks_diff(now, last_check) >= RECHECK_SECONDS * 1000:
            last_check = now
            fresh = get_status()
            if fresh is not None and fresh.get("dose_id") != status.get("dose_id"):
                return None
        time.sleep_ms(50)
    pressed_at = time.ticks_ms()
    while switch.value() == 0:
        time.sleep_ms(50)
    time.sleep_ms(200)
    return pressed_at

# ==========================================
# ONLINE WORKFLOW: THE BACKEND DECIDES WHEN A DOSE IS DUE
# ==========================================
def online_loop():
    after_drop = False   # a drop and its countdown just finished
    last_flag = None

    while True:
        status = get_status()
        if status is None:
            led_red.value(0)
            led_green.value(0)
            lcd.show("No connection", "Retrying...")
            time.sleep(POLL_SECONDS)
            continue

        if pending_drops:
            flush_drops()

        if status.get("dose_due"):
            # ALARM: green LED on when this is the next drop after a countdown
            led_red.value(0)
            led_green.value(1 if after_drop else 0)
            print("\n[ALARM] >>> TIME FOR EYE DROPS:", status.get("medication"), "<<<")
            pressed_at = wait_for_drop(status)
            led_green.value(0)
            if pressed_at is None:
                after_drop = False
                continue

            last_flag = log_drop(pressed_at)
            lcd.display("Drop applied!", FLAG_TEXT.get(last_flag, "Saved offline"))
            time.sleep(2)

            countdown_between_drops("Drop applied!")
            after_drop = True
            continue

        if after_drop:
            # DOSE COMPLETED: no more drops due right now
            led_green.value(1)
            lcd.display("Dose Completed!", "Great job!" if last_flag == "on_time" else "Drops logged")
            print("\n[SUCCESS] All due drops recorded.")
            time.sleep(5)
            led_green.value(0)
            after_drop = False

        # STANDBY
        led_red.value(0)
        led_green.value(0)
        if status.get("next_time"):
            lcd.show("Next schedule:", status["next_time"])
        else:
            lcd.show("No more drops", "today")
        time.sleep(POLL_SECONDS)

# ==========================================
# OFFLINE DEMO WORKFLOW (no config.py)
# ==========================================
def offline_demo_loop():
    current_dose_index = 0

    while True:
        # ----------------------------------------------------
        # STAGE 1: STANDBY (WAITING FOR SCHEDULED DOSE TIME)
        # ----------------------------------------------------
        led_red.value(0)
        led_green.value(0)

        next_time = DOCTOR_SCHEDULE[current_dose_index]
        lcd.display("Next schedule:", next_time)
        print(f"\n[STANDBY] Displaying next scheduled dose: {next_time}")
        print(f"[STANDBY] Waiting {TIME_UNTIL_NEXT_DOSE} seconds until medication time arrives...")

        # Wait until scheduled time arrives automatically
        time.sleep(TIME_UNTIL_NEXT_DOSE)

        # ----------------------------------------------------
        # STAGE 2: AUTOMATIC ALARM (TIME FOR MEDICATION)
        # ----------------------------------------------------
        lcd.display("Time to take", "your eye drops!")
        print("\n[ALARM] >>> TIME FOR EYE DROPS! <<<")
        print("[ALARM] Waiting for patient to apply Drop 1 and press switch...")

        # Patient applies Drop 1 and presses switch to confirm
        wait_for_switch_press()

        # ----------------------------------------------------
        # STAGE 3: DROP 1 CONFIRMED -> COUNTDOWN INTERVAL
        # ----------------------------------------------------
        countdown_between_drops("Drop 1 applied!")

        # ----------------------------------------------------
        # STAGE 4: INTERVAL FINISHED -> READY FOR DROP 2
        # ----------------------------------------------------
        led_green.value(1)  # Green LED ON: safe to apply drop 2
        lcd.display("Ready for Drop 2", "Press to confirm")
        print("\n[READY] Safe interval completed! Patient applies Drop 2.")

        # Patient applies Drop 2 and presses switch to confirm
        wait_for_switch_press()

        # ----------------------------------------------------
        # STAGE 5: DOSE COMPLETED -> ADVANCE TO NEXT SCHEDULE
        # ----------------------------------------------------
        lcd.display("Dose Completed!", "Great job!")
        print("\n[SUCCESS] Both drops recorded. Dose logged successfully!")

        # Keep Green LED and congratulations visible for 5 seconds
        time.sleep(5)
        led_green.value(0)

        # Advance to the doctor's next scheduled time
        current_dose_index = (current_dose_index + 1) % len(DOCTOR_SCHEDULE)
        print(f"[SCHEDULE] Advancing to next prescribed time: {DOCTOR_SCHEDULE[current_dose_index]}")

        # Automatically loops back to STAGE 1 with the new schedule!

# ==========================================
# MAIN CONTINUOUS HEALTHCARE WORKFLOW
# ==========================================
print("\n=== OFTACARE DISPENSER SYSTEM RUNNING ===")

if config is None:
    print("[MODE] No config.py found: running the offline demo")
    offline_demo_loop()
else:
    print("[MODE] Online: backend", config.BACKEND_URL)
    online_loop()
