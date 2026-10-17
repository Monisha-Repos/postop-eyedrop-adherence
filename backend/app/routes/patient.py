"""Endpoints for the patient view of the iPad app. A patient only ever sees their own data."""
import uuid
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from .. import config, doses, reminders, tts
from ..auth import User, require_patient
from ..db import get_conn

router = APIRouter(prefix="/patient", tags=["patient"])

# reminder_id -> script, so the audio endpoint speaks exactly the text the app was shown.
_scripts: dict[str, str] = {}
_SCRIPTS_MAX = 500


def _patient(conn, user: User) -> dict:
    return conn.execute(
        "SELECT id, first_name, timezone, humor_level FROM patients WHERE id = %s", (user.id,)
    ).fetchone()


def _time_label(at: datetime, tz_name: str) -> str:
    t = at.astimezone(ZoneInfo(tz_name))
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def _refresh(conn, patient: dict) -> None:
    doses.ensure_doses(conn, patient["id"], patient["timezone"])
    doses.sweep_missed(conn)


@router.get("/today")
def today(user: User = Depends(require_patient), conn=Depends(get_conn)):
    patient = _patient(conn, user)
    _refresh(conn, patient)
    now = doses.now_utc()
    start, end = doses.local_day_bounds(patient["timezone"], doses.local_today(patient["timezone"]))
    return {
        "due_dose": doses.due_dose(conn, patient["id"], now),
        "next_dose": doses.next_dose(conn, patient["id"], now),
        "doses": doses.doses_between(conn, patient["id"], start, end),
    }


@router.get("/reminder")
def reminder(user: User = Depends(require_patient), conn=Depends(get_conn)):
    """The reminder to speak right now: the due dose, else the result of the latest dose, else the next one."""
    patient = _patient(conn, user)
    _refresh(conn, patient)
    now = doses.now_utc()
    tz = patient["timezone"]
    upcoming = doses.next_dose(conn, patient["id"], now)
    next_label = f"{upcoming['medication']} at {_time_label(upcoming['scheduled_at'], tz)}" if upcoming else None

    dose = doses.due_dose(conn, patient["id"], now)
    flag = "due" if dose else None
    if not dose:
        dose = doses.latest_resolved(conn, patient["id"], since=now - timedelta(hours=2))
        flag = dose["flag"] if dose else None

    if not dose:
        text = f"No drops are due right now. Your next drop is {next_label}." if next_label else "No more drops today."
        rem = reminders.Reminder("none", text, f"Hello {patient['first_name']}.", "", "plain")
    else:
        meds = conn.execute(
            "SELECT DISTINCT m.name FROM schedules s JOIN medications m ON m.id = s.medication_id WHERE s.patient_id = %s",
            (patient["id"],),
        ).fetchall()
        minutes_off = None
        if dose["lifted_at"]:
            minutes_off = round((dose["lifted_at"] - dose["scheduled_at"]).total_seconds() / 60)
        ctx = reminders.ReminderContext(
            first_name=patient["first_name"],
            flag=flag,
            medication=dose["medication"],
            drops=dose["drops"],
            eye=dose["eye"],
            time_label=_time_label(dose["scheduled_at"], tz),
            minutes_off=minutes_off,
            next_label=next_label,
            all_medications=[m["name"] for m in meds],
        )
        rem = reminders.build_reminder(ctx, patient["humor_level"])

    reminder_id = uuid.uuid4().hex
    if len(_scripts) >= _SCRIPTS_MAX:
        _scripts.pop(next(iter(_scripts)))
    _scripts[reminder_id] = rem.script
    return {
        "reminder_id": reminder_id,
        "dose_id": dose["id"] if dose else None,
        "flag": rem.flag,
        "instruction": rem.instruction,
        "script": rem.script,
        "source": rem.source,
        "has_audio": bool(config.GEMINI_API_KEY),
    }


@router.get("/reminder/{reminder_id}/audio")
def reminder_audio(reminder_id: str, user: User = Depends(require_patient)):
    script = _scripts.get(reminder_id)
    if not script:
        raise HTTPException(404, "Unknown reminder")
    audio = tts.synthesize(script)
    if audio is None:
        raise HTTPException(503, "Speech unavailable; use on-device voice")
    return Response(content=audio, media_type="audio/wav")


class Settings(BaseModel):
    humor_level: Literal["full", "mild", "off"]


@router.patch("/settings")
def update_settings(body: Settings, user: User = Depends(require_patient), conn=Depends(get_conn)):
    conn.execute("UPDATE patients SET humor_level = %s WHERE id = %s", (body.humor_level, user.id))
    return {"humor_level": body.humor_level}
