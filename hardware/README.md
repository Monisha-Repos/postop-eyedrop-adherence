# Dock hardware

The firmware is MicroPython: [firmware/main.py](../firmware/main.py). Pin numbers, timings and the dose schedule are set at the top of that file.

The dock runs on its own. It has no WiFi and does not talk to the backend, so doses confirmed on the dock are not recorded in the app.

## Pin map (ESP32 DevKit V1)

| Part | ESP32 pin | Wiring |
| --- | --- | --- |
| Micro switch (confirm button) | GPIO 13 (D13) | One leg → GPIO 13, other leg → GND. Internal pull-up; **pressed = LOW**. |
| Red LED (wait between drops) | GPIO 25 (D25) | GPIO → 220 Ω → LED anode; LED cathode → GND |
| Green LED (ready for drop 2 / dose done) | GPIO 26 (D26) | GPIO → 220 Ω → LED anode; LED cathode → GND |
| LCD1602 with I2C backpack (PCF8574) | SDA → GPIO 21 (D21), SCL → GPIO 22 (D22) | VCC → 5 V (VIN), GND → GND. I2C address 0x27 or 0x3F is detected automatically. |
| Power | USB 5 V | |

If the LCD isn't found on the I2C bus, the firmware keeps running and prints the screen text to the serial console instead.

## Behaviour

Each dose is two drops with a safety wait between them.

| Stage | LCD | Red | Green | Waits for |
| --- | --- | --- | --- | --- |
| 1. Standby | "Next schedule:" + next time | off | off | `TIME_UNTIL_NEXT_DOSE` seconds (10 s demo) |
| 2. Alarm | "Time to take your eye drops!" | off | off | Switch press (drop 1 applied) |
| 3. Interval | "Drop 1 applied!" + countdown | on | off | `WAIT_BETWEEN_DROPS` seconds (20 s demo, 300 s = 5 min real) |
| 4. Ready | "Ready for Drop 2 / Press to confirm" | off | on | Switch press (drop 2 applied) |
| 5. Done | "Dose Completed!" | off | on for 5 s | Then moves to the next time in `DOCTOR_SCHEDULE` and back to stage 1 |

`DOCTOR_SCHEDULE` (08:00 AM, 02:00 PM, 08:00 PM) is only shown on the LCD. The ESP32 has no real-time clock, so the alarm fires after the standby timer, not at the actual time of day.

## Flashing

```powershell
pip install esptool mpremote
# Flash MicroPython for ESP32 from micropython.org, then:
cd firmware
mpremote cp main.py :main.py
mpremote reset
mpremote repl        # watch the console output
```

## Enclosure

- STL files: TODO, put them in this folder.
