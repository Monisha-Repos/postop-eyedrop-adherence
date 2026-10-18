from machine import Pin, SoftI2C
import time

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

# Doctor's prescribed schedule list
DOCTOR_SCHEDULE = ["08:00 AM", "02:00 PM", "08:00 PM"]
current_dose_index = 0

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

lcd = LCD1602(PIN_SDA, PIN_SCL)

def wait_for_switch_press():
    """Wait for patient to press the micro switch to confirm a dose."""
    while switch.value() == 1:
        time.sleep_ms(50)
    while switch.value() == 0:
        time.sleep_ms(50)
    time.sleep_ms(200)

# ==========================================
# MAIN CONTINUOUS HEALTHCARE WORKFLOW
# ==========================================
print("\n=== OFTACARE DISPENSER SYSTEM RUNNING ===")

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
    led_red.value(1)    # Red LED ON: absorption wait active
    led_green.value(0)
    print("\n[INTERVAL] Drop 1 confirmed. Starting safety countdown...")

    for remaining in range(WAIT_BETWEEN_DROPS, 0, -1):
        mins = remaining // 60
        secs = remaining % 60
        lcd.display("Drop 1 applied!", "Wait: {:02d}:{:02d} min".format(mins, secs))
        time.sleep(1)

    # ----------------------------------------------------
    # STAGE 4: INTERVAL FINISHED -> READY FOR DROP 2
    # ----------------------------------------------------
    led_red.value(0)    # Red LED OFF
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
