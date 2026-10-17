# Dock hardware

The firmware is MicroPython: [firmware/main.py](../firmware/main.py). Pin numbers are set at the top of that file.

## Pin map (ESP32 DevKit V1)

| Part | ESP32 pin | Wiring |
| --- | --- | --- |
| Green LED (waiting) | GPIO 25 | GPIO → 220 Ω → LED anode; LED cathode → GND |
| Red LED (dose due / offline blink) | GPIO 26 | GPIO → 220 Ω → LED anode; LED cathode → GND |
| Passive buzzer or speaker | GPIO 27 | Buzzer + → GPIO 27, − → GND. A speaker needs an NPN transistor (e.g. 2N2222) and a ~100 Ω series resistor. |
| Lift switch (push button under the cup) | GPIO 14 | One leg → GPIO 14, other leg → GND. Internal pull-up; **pressed (LOW) = bottle in the cup**. |
| Big silence button | GPIO 33 | One leg → GPIO 33, other leg → GND. Internal pull-up. |
| Power | USB 5 V | |

Pins avoided on purpose: GPIO 0, 2, 12 and 15 are boot-strapping pins; GPIO 34 to 39 are input-only with no pull-ups.

## Enclosure

- Box with the ESP32 inside and the two LEDs visible on the front.
- Fitted cup for the bottle, with a plunger that presses the lift switch under the bottle's weight.
- Large button cap over the silence button.
- STL files: TODO, put them in this folder.

## Behaviour

| State | Green | Red | Sound |
| --- | --- | --- | --- |
| Waiting, nothing due | on | off | none |
| Dose due | off | on | 3 beeps every 20 s until the bottle is lifted or the button is pressed |
| No WiFi | off | slow blink | none |
