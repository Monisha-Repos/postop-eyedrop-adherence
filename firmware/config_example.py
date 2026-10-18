# Copy to config.py, fill in, and upload it to the ESP32 next to main.py. config.py is git-ignored.
# Without config.py on the ESP32, the dock runs the offline demo instead.

WIFI_SSID = "your-wifi"         # 2.4 GHz network; the ESP32 can't join 5 GHz
WIFI_PASSWORD = "your-password"

# Backend base URL, no trailing slash. Use the laptop's LAN IP (run ipconfig), not localhost.
BACKEND_URL = "http://192.168.1.20:8000"

# Must match DEVICE_TOKEN in backend/.env. Register it once with:
#   python -m scripts.register_device      (from backend/)
DEVICE_TOKEN = "change-me-to-a-long-random-string"
