# Copy to config.py, fill in, and upload both files to the ESP32. config.py is git-ignored.

WIFI_SSID = "your-wifi"
WIFI_PASSWORD = "your-password"

# Backend base URL, no trailing slash. On a LAN demo use the laptop's IP.
BACKEND_URL = "http://192.168.1.20:8000"

# Must match DEVICE_TOKEN in backend/.env (the seed script registers it).
DEVICE_TOKEN = "change-me-to-a-long-random-string"
