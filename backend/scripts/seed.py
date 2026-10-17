"""Load demo data: one provider, two patients, a typical post-cataract regimen and dose history.

Run from backend/:  python -m scripts.seed            (re-running replaces the demo data)
                    python -m scripts.seed --due-now   (also makes a dose due right now, for a live dock demo)
"""
import argparse
import random
from datetime import date, time, timedelta
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from app import config, rules
from app.auth import hash_device_token
from app.doses import local_today, now_utc

TZ = "America/New_York"
QID = [time(8), time(12), time(16), time(20)]  # four times a day

MEDICATIONS = [
    ("Moxifloxacin", "antibiotic"),
    ("Prednisolone", "steroid"),
    ("Ketorolac", "anti-inflammatory"),
]


def regimen(surgery: date) -> dict[str, list[tuple[date, date, list[time]]]]:
    """Medication -> steps (start, end inclusive, times). Prednisolone tapers weekly."""
    week = lambda n: (surgery + timedelta(days=7 * n), surgery + timedelta(days=7 * n + 6))  # noqa: E731
    return {
        "Moxifloxacin": [(*week(0), QID)],
        "Prednisolone": [
            (*week(0), QID),
            (*week(1), [time(8), time(14), time(20)]),
            (*week(2), [time(8), time(20)]),
            (*week(3), [time(8)]),
        ],
        "Ketorolac": [(surgery, surgery + timedelta(days=27), QID)],
    }


def random_outcome(rng: random.Random, scheduled_at):
    """Plausible history: mostly on time, some late, a few early or missed."""
    r = rng.random()
    if r < 0.70:
        return "on_time", scheduled_at + timedelta(minutes=rng.randint(-10, 20))
    if r < 0.82:
        return "late", scheduled_at + timedelta(minutes=rng.randint(40, 150))
    if r < 0.88:
        return "early", scheduled_at - timedelta(minutes=rng.randint(40, 100))
    return "missed", None


def seed_patient(cur, rng, provider_id, sub, first, last, eye, days_since_surgery, med_ids):
    today = local_today(TZ)
    surgery = today - timedelta(days=days_since_surgery)
    patient_id = cur.execute(
        """
        INSERT INTO patients (auth0_sub, first_name, last_name, provider_id, timezone, surgery_date)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """,
        (sub, first, last, provider_id, TZ, surgery),
    ).fetchone()["id"]

    steps = []
    for med, med_steps in regimen(surgery).items():
        schedule_id = cur.execute(
            "INSERT INTO schedules (patient_id, medication_id, eye, drops) VALUES (%s, %s, %s, 1) RETURNING id",
            (patient_id, med_ids[med], eye),
        ).fetchone()["id"]
        for start, end, times in med_steps:
            cur.execute(
                "INSERT INTO schedule_steps (schedule_id, start_date, end_date, dose_times) VALUES (%s, %s, %s, %s)",
                (schedule_id, start, end, times),
            )
            steps.append(rules.Step(schedule_id, start, end, tuple(times)))

    # Dose rows from surgery day through tomorrow, with made-up outcomes for the past.
    now = now_utc()
    tz = ZoneInfo(TZ)
    day = surgery
    while day <= today + timedelta(days=1):
        for schedule_id, at in rules.planned_doses(steps, day, tz):
            flag, lifted = ("pending", None)
            if rules.is_missed(at, now):
                flag, lifted = random_outcome(rng, at)
            returned = lifted + timedelta(seconds=rng.randint(20, 90)) if lifted else None
            cur.execute(
                """
                INSERT INTO dose_events (patient_id, schedule_id, scheduled_at, lifted_at, returned_at, flag)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (patient_id, schedule_id, at, lifted, returned, flag),
            )
        day += timedelta(days=1)

    # A couple of extra lifts that matched no dose.
    for days_ago in (2, 4):
        at = now - timedelta(days=days_ago, hours=rng.randint(1, 5))
        cur.execute(
            """
            INSERT INTO dose_events (patient_id, schedule_id, scheduled_at, lifted_at, returned_at, flag)
            VALUES (%s, NULL, %s, %s, %s, 'too_frequent')
            """,
            (patient_id, at, at, at + timedelta(seconds=30)),
        )
    return patient_id, steps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--due-now", action="store_true", help="add a pending dose scheduled one minute ago")
    args = parser.parse_args()
    if not config.DEVICE_TOKEN:
        raise SystemExit("Set DEVICE_TOKEN in backend/.env first.")

    rng = random.Random(42)
    with psycopg.connect(config.DATABASE_URL, row_factory=dict_row) as conn, conn.cursor() as cur:
        demo_subs = [config.DEMO_PATIENT_SUB, "auth0|demo-patient-2"]
        cur.execute("DELETE FROM patients WHERE auth0_sub = ANY(%s)", (demo_subs,))
        cur.execute("DELETE FROM providers WHERE auth0_sub = %s", (config.DEMO_PROVIDER_SUB,))

        med_ids = {}
        for name, purpose in MEDICATIONS:
            med_ids[name] = cur.execute(
                """
                INSERT INTO medications (name, purpose) VALUES (%s, %s)
                ON CONFLICT (name) DO UPDATE SET purpose = EXCLUDED.purpose RETURNING id
                """,
                (name, purpose),
            ).fetchone()["id"]

        provider_id = cur.execute(
            "INSERT INTO providers (auth0_sub, name) VALUES (%s, %s) RETURNING id",
            (config.DEMO_PROVIDER_SUB, "Dr. Rivera"),
        ).fetchone()["id"]

        ann_id, ann_steps = seed_patient(cur, rng, provider_id, config.DEMO_PATIENT_SUB, "Ann", "Lee", "left", 5, med_ids)
        seed_patient(cur, rng, provider_id, "auth0|demo-patient-2", "George", "Patel", "right", 12, med_ids)

        cur.execute(
            "INSERT INTO devices (patient_id, token_sha256) VALUES (%s, %s)",
            (ann_id, hash_device_token(config.DEVICE_TOKEN)),
        )

        if args.due_now:
            at = now_utc().replace(second=0, microsecond=0) - timedelta(minutes=1)
            cur.execute(
                "INSERT INTO dose_events (patient_id, schedule_id, scheduled_at) VALUES (%s, %s, %s)",
                (ann_id, ann_steps[0].schedule_id, at),
            )
            print(f"Added a pending dose for Ann at {at.isoformat()}")

    # Continuous aggregate refresh cannot run inside a transaction.
    with psycopg.connect(config.DATABASE_URL, autocommit=True) as conn:
        conn.execute("CALL refresh_continuous_aggregate('daily_adherence', NULL, NULL)")

    print("Seeded: provider Dr. Rivera, patients Ann Lee (has the dock) and George Patel.")


if __name__ == "__main__":
    main()
