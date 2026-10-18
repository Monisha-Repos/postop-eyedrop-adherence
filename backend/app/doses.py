"""Database side of dose tracking: turning schedules into dose rows and applying dock events."""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import rules

# (patient_id, local day) pairs already materialized by this process. Inserts are
# idempotent anyway; this only avoids repeating them on every 15-second dock poll.
_materialized: set[tuple[int, date]] = set()

# A dock retry re-sends the same event with the same timestamp, so a short window is
# enough. Keep it below the dock's wait between drops (20 s in the demo).
DUPLICATE_LIFT_WINDOW = timedelta(seconds=10)
DOSE_SELECT = """
    SELECT d.id, d.scheduled_at, d.lifted_at, d.returned_at, d.flag,
           m.name AS medication, s.eye, s.drops
    FROM dose_events d
    LEFT JOIN schedules s ON s.id = d.schedule_id
    LEFT JOIN medications m ON m.id = s.medication_id
"""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def time_label(at: datetime, tz_name: str) -> str:
    """Local wall-clock time, e.g. "2:00 PM"."""
    t = at.astimezone(ZoneInfo(tz_name))
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def local_today(tz_name: str) -> date:
    return now_utc().astimezone(ZoneInfo(tz_name)).date()


def ensure_doses(conn, patient_id: int, tz_name: str, days_back: int = 7, days_ahead: int = 1) -> None:
    """Create pending dose rows for the patient's schedule from `days_back` days ago through tomorrow.

    Rows for past days become 'missed' on the next sweep, so a dock that was
    offline all day still shows up as missed doses on the provider dashboard.
    """
    tz = ZoneInfo(tz_name)
    today = local_today(tz_name)
    todo = [today + timedelta(days=d) for d in range(-days_back, days_ahead + 1)]
    todo = [d for d in todo if (patient_id, d) not in _materialized]
    if not todo:
        return

    rows = conn.execute(
        """
        SELECT st.schedule_id, st.start_date, st.end_date, st.dose_times
        FROM schedule_steps st JOIN schedules s ON s.id = st.schedule_id
        WHERE s.patient_id = %s
        """,
        (patient_id,),
    ).fetchall()
    steps = [rules.Step(r["schedule_id"], r["start_date"], r["end_date"], tuple(r["dose_times"])) for r in rows]
    slots = [slot for day in todo for slot in rules.planned_doses(steps, day, tz)]
    if slots:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO dose_events (patient_id, schedule_id, scheduled_at) VALUES (%s, %s, %s)
                ON CONFLICT (schedule_id, scheduled_at) DO NOTHING
                """,
                [(patient_id, schedule_id, at) for schedule_id, at in slots],
            )
    _materialized.update((patient_id, d) for d in todo)


def sweep_missed(conn) -> None:
    """Mark every pending dose older than MISSED_AFTER as missed (all patients)."""
    now = now_utc()
    conn.execute(
        "UPDATE dose_events SET flag = 'missed' WHERE flag = 'pending' AND scheduled_at < %s AND scheduled_at > %s",
        (now - rules.MISSED_AFTER, now - timedelta(days=30)),
    )


def record_lift(conn, patient_id: int, lifted_at: datetime) -> dict:
    """Match a bottle lift to a pending dose and flag it. Returns {dose_id, flag}."""
    # Ignore a repeated lift (e.g. the dock retrying after a WiFi hiccup).
    recent = conn.execute(
        """
        SELECT id, flag FROM dose_events
        WHERE patient_id = %s AND lifted_at IS NOT NULL
          AND lifted_at BETWEEN %s AND %s
        ORDER BY lifted_at DESC LIMIT 1
        """,
        (patient_id, lifted_at - DUPLICATE_LIFT_WINDOW, lifted_at + DUPLICATE_LIFT_WINDOW),
    ).fetchone()
    if recent:
        return {"dose_id": recent["id"], "flag": recent["flag"]}

    rows = conn.execute(
        """
        SELECT id, scheduled_at FROM dose_events
        WHERE patient_id = %s AND flag = 'pending' AND scheduled_at BETWEEN %s AND %s
        FOR UPDATE
        """,
        (patient_id, lifted_at - rules.MISSED_AFTER, lifted_at + rules.EARLY_LIMIT),
    ).fetchall()
    pending = [rules.PendingDose(r["id"], r["scheduled_at"]) for r in rows]
    dose = rules.choose_dose(pending, lifted_at)

    if dose is None:
        row = conn.execute(
            """
            INSERT INTO dose_events (patient_id, schedule_id, scheduled_at, lifted_at, flag)
            VALUES (%s, NULL, %s, %s, 'too_frequent') RETURNING id
            """,
            (patient_id, lifted_at, lifted_at),
        ).fetchone()
        return {"dose_id": row["id"], "flag": "too_frequent"}

    flag = rules.classify_lift(dose.scheduled_at, lifted_at)
    conn.execute(
        "UPDATE dose_events SET lifted_at = %s, flag = %s WHERE id = %s AND scheduled_at = %s",
        (lifted_at, flag, dose.id, dose.scheduled_at),
    )
    return {"dose_id": dose.id, "flag": flag}


def record_return(conn, patient_id: int, returned_at: datetime) -> int | None:
    """Attach a bottle return to the most recent lift (within 30 min) that has no return yet."""
    row = conn.execute(
        """
        UPDATE dose_events SET returned_at = %s
        WHERE (id, scheduled_at) = (
            SELECT id, scheduled_at FROM dose_events
            WHERE patient_id = %s AND lifted_at IS NOT NULL AND returned_at IS NULL
              AND lifted_at BETWEEN %s AND %s
            ORDER BY lifted_at DESC LIMIT 1
        )
        RETURNING id
        """,
        (returned_at, patient_id, returned_at - timedelta(minutes=30), returned_at),
    ).fetchone()
    return row["id"] if row else None


def due_dose(conn, patient_id: int, now: datetime) -> dict | None:
    """The oldest pending dose that is due right now (what the dock alarms for)."""
    return conn.execute(
        DOSE_SELECT
        + " WHERE d.patient_id = %s AND d.flag = 'pending' AND d.scheduled_at <= %s AND d.scheduled_at > %s"
        + " ORDER BY d.scheduled_at LIMIT 1",
        (patient_id, now, now - rules.MISSED_AFTER),
    ).fetchone()


def next_dose(conn, patient_id: int, now: datetime) -> dict | None:
    return conn.execute(
        DOSE_SELECT + " WHERE d.patient_id = %s AND d.flag = 'pending' AND d.scheduled_at > %s"
        " ORDER BY d.scheduled_at LIMIT 1",
        (patient_id, now),
    ).fetchone()


def latest_resolved(conn, patient_id: int, since: datetime) -> dict | None:
    """Most recent dose that got a result (taken, or swept to missed) since `since`."""
    return conn.execute(
        DOSE_SELECT
        + " WHERE d.patient_id = %s AND d.flag <> 'pending'"
        "   AND COALESCE(d.lifted_at, d.scheduled_at + %s) >= %s"
        " ORDER BY COALESCE(d.lifted_at, d.scheduled_at + %s) DESC LIMIT 1",
        (patient_id, rules.MISSED_AFTER, since, rules.MISSED_AFTER),
    ).fetchone()


def doses_between(conn, patient_id: int, start: datetime, end: datetime) -> list[dict]:
    return conn.execute(
        DOSE_SELECT + " WHERE d.patient_id = %s AND d.scheduled_at >= %s AND d.scheduled_at < %s"
        " ORDER BY d.scheduled_at",
        (patient_id, start, end),
    ).fetchall()


def local_day_bounds(tz_name: str, day: date) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    start = datetime.combine(day, datetime.min.time(), tzinfo=tz)
    return start, start + timedelta(days=1)
