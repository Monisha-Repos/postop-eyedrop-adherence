# Dock hardware

The firmware is MicroPython: [firmware/main.py](../firmware/main.py). Pin numbers and timings are set at the top of that file.

The dock has two modes, picked automatically when it starts:

- **Online** (a `config.py` with WiFi and backend settings is on the ESP32): the backend decides when a dose is due and which drop it is. Each switch press is saved to the database, so it shows up in the app and on the doctor dashboard.
- **Offline demo** (no `config.py`): runs on its own with a fixed schedule and timers. Nothing is saved.

## Pin map (ESP32 DevKit V1)

| Part | ESP32 pin | Wiring |
| --- | --- | --- |
| Micro switch (confirm button) | GPIO 13 (D13) | One leg → GPIO 13, other leg → GND. Internal pull-up; **pressed = LOW**. |
| Red LED (wait between drops) | GPIO 25 (D25) | GPIO → 220 Ω → LED anode; LED cathode → GND |
| Green LED (ready for next drop / dose done) | GPIO 26 (D26) | GPIO → 220 Ω → LED anode; LED cathode → GND |
| LCD1602 with I2C backpack (PCF8574) | SDA → GPIO 21 (D21), SCL → GPIO 22 (D22) | VCC → 5 V (VIN), GND → GND. I2C address 0x27 or 0x3F is detected automatically. |
| Power | USB 5 V | |

If the LCD isn't found on the I2C bus, the firmware keeps running and prints the screen text to the serial console instead.

## Behaviour: online

The dock asks the backend every 15 s (`GET /device/status`) whether a dose is due.

| Stage | LCD | Red | Green | What happens |
| --- | --- | --- | --- | --- |
| Standby | "Next schedule:" + next dose time from the backend | off | off | Keeps checking every 15 s |
| Alarm | Alternates "Time to take your eye drops!" and the medication + "1 drop, left eye" | off | on if it follows another drop | Waits for a switch press. If the dose stops being due (missed after 3 h), it goes back to standby. |
| Drop applied | "Drop applied!" + the result ("Logged: on time", "late", "early") | off | off | The press is sent as `POST /device/events`. Without a connection it shows "Saved offline" and is sent later with the right time. |
| Interval | "Drop applied!" + countdown | on | off | `WAIT_BETWEEN_DROPS` seconds (20 s demo, 300 s = 5 min real), then the next due drop alarms |
| Done | "Dose Completed!" | off | on for 5 s | When no more drops are due |
| No connection | "No connection / Retrying..." | off | off | Retries every 15 s |

Drops scheduled at the same time are 5 minutes apart in the backend (e.g. 8:00, 8:05, 8:10), so with the 20 s demo wait the next drop shows as "Next schedule" until its time comes.

## Behaviour: offline demo

Each dose is two drops with a safety wait between them.

| Stage | LCD | Red | Green | Waits for |
| --- | --- | --- | --- | --- |
| 1. Standby | "Next schedule:" + next time | off | off | `TIME_UNTIL_NEXT_DOSE` seconds (10 s demo) |
| 2. Alarm | "Time to take your eye drops!" | off | off | Switch press (drop 1 applied) |
| 3. Interval | "Drop 1 applied!" + countdown | on | off | `WAIT_BETWEEN_DROPS` seconds |
| 4. Ready | "Ready for Drop 2 / Press to confirm" | off | on | Switch press (drop 2 applied) |
| 5. Done | "Dose Completed!" | off | on for 5 s | Then moves to the next time in `DOCTOR_SCHEDULE` and back to stage 1 |

`DOCTOR_SCHEDULE` (08:00 AM, 02:00 PM, 08:00 PM) is only shown on the LCD. The ESP32 has no real-time clock, so the alarm fires after the standby timer, not at the actual time of day.

## Setup and flashing

1. **Backend:** start it so the ESP32 can reach it over WiFi (`--host 0.0.0.0`), and register the dock's token once:
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   python -m scripts.register_device     # links DEVICE_TOKEN in backend/.env to the demo patient (Ann)
   $env:DEV_AUTH_BYPASS = "true"
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   If Windows asks whether to allow Python on the network, allow it on private networks.
2. **Dock config:** copy [firmware/config_example.py](../firmware/config_example.py) to `firmware/config.py` and fill in the WiFi (2.4 GHz), `BACKEND_URL` (your laptop's IP from `ipconfig`, e.g. `http://192.168.1.20:8000`) and the same `DEVICE_TOKEN` as `backend/.env`.
3. **Flash:**
   ```powershell
   pip install esptool mpremote
   # Flash MicroPython (>= 1.20) for ESP32 from micropython.org, then:
   cd firmware
   mpremote cp config.py :config.py      # skip for the offline demo
   mpremote cp main.py :main.py
   mpremote reset
   mpremote repl                         # watch the console output
   ```
   To go back to the offline demo, remove the config: `mpremote rm :config.py`, then `mpremote reset`.

## Enclosure

- STL files: TODO, put them in this folder.
