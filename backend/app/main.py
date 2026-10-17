"""Eye Spy backend. Run from backend/:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .auth import User, current_user
from .db import get_conn, pool
from .routes import device, patient, provider

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("eyespy")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if config.DEV_AUTH_BYPASS:
        log.warning("DEV_AUTH_BYPASS is ON: 'Bearer dev:<sub>' tokens are accepted. Local demos only.")
    pool.open()
    yield
    pool.close()


app = FastAPI(title="Eye Spy API", lifespan=lifespan)
# The React app runs on a different origin (Vite dev server or static host).
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "PATCH", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(device.router)
app.include_router(patient.router)
app.include_router(provider.router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/me")
def me(user: User = Depends(current_user), conn=Depends(get_conn)):
    """Tells the app which view to show."""
    body = {"role": user.role, "name": user.name, "humor_level": None}
    if user.role == "patient":
        row = conn.execute("SELECT humor_level FROM patients WHERE id = %s", (user.id,)).fetchone()
        body["humor_level"] = row["humor_level"]
    return body
