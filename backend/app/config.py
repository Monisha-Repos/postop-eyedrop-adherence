"""Settings read from the environment (and backend/.env when python-dotenv is installed)."""
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # lets the pure-logic unit tests run on a bare Python install
    pass


def _bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "")
AUTH0_ROLES_CLAIM = os.getenv("AUTH0_ROLES_CLAIM", "https://eyespy.app/roles")

DATABASE_URL = os.getenv("DATABASE_URL", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_TTS_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
GEMINI_TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Sulafat")

DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "")
DEMO_PATIENT_SUB = os.getenv("DEMO_PATIENT_SUB", "auth0|demo-patient")
DEMO_PROVIDER_SUB = os.getenv("DEMO_PROVIDER_SUB", "auth0|demo-provider")

DEV_AUTH_BYPASS = _bool("DEV_AUTH_BYPASS")

# Web app origins allowed to call the API from the browser (comma-separated).
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
