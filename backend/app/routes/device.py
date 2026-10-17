"""Endpoints the ESP32 dock calls. Authenticated with the X-Device-Token header."""
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import doses
from ..auth import current_device
from ..db import get_conn

router = APIRouter(prefix="/device", tags=["device"])


@router.get("/status")
def status(device=Depends(current_device), conn=Depends(get_conn)):
    """Polled every ~15 s. `dose_due` turns the red LED and alarm on."""
    now = doses.now_utc()
    doses.ensure_doses(conn, device["patient_id"], device["timezone"])
    doses.sweep_missed(conn)
    conn.execute("UPDATE devices SET last_seen_at = %s WHERE id = %s", (now, device["id"]))
    due = doses.due_dose(conn, device["patient_id"], now)
    return {
        "dose_due": due is not None,
        "dose_id": due["id"] if due else None,
        "medication": due["medication"] if due else None,
        "scheduled_at": due["scheduled_at"] if due else None,
        "server_time": now,
    }


class DeviceEvent(BaseModel):
    event: Literal["lifted", "returned"]
    # How long ago the event happened, by the dock's own clock. Lets the dock
    # queue events while WiFi is down without needing a real-time clock.
    age_ms: int = Field(default=0, ge=0, le=24 * 3600 * 1000)


@router.post("/events")
def post_event(body: DeviceEvent, device=Depends(current_device), conn=Depends(get_conn)):
    at = doses.now_utc() - timedelta(milliseconds=body.age_ms)
    conn.execute(
        "INSERT INTO device_events (device_id, patient_id, event, at) VALUES (%s, %s, %s, %s)",
        (device["id"], device["patient_id"], body.event, at),
    )
    if body.event == "lifted":
        doses.ensure_doses(conn, device["patient_id"], device["timezone"])
        return {"event": "lifted", "at": at, **doses.record_lift(conn, device["patient_id"], at)}
    return {"event": "returned", "at": at, "dose_id": doses.record_return(conn, device["patient_id"], at)}
