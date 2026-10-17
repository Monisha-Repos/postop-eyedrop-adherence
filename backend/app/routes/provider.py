"""Endpoints for the provider view. Every query is scoped to patients.provider_id = the signed-in provider."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import doses
from ..auth import User, require_provider
from ..db import get_conn

router = APIRouter(prefix="/provider", tags=["provider"])


def _own_patient(conn, user: User, patient_id: int) -> dict:
    row = conn.execute(
        "SELECT id, first_name, last_name, timezone, surgery_date FROM patients WHERE id = %s AND provider_id = %s",
        (patient_id, user.id),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Patient not found")  # 404, not 403: don't reveal other providers' patients
    doses.ensure_doses(conn, row["id"], row["timezone"])
    return row


@router.get("/patients")
def list_patients(user: User = Depends(require_provider), conn=Depends(get_conn)):
    patients = conn.execute(
        "SELECT id, first_name, last_name, timezone, surgery_date FROM patients WHERE provider_id = %s ORDER BY last_name",
        (user.id,),
    ).fetchall()
    for p in patients:
        doses.ensure_doses(conn, p["id"], p["timezone"])
    doses.sweep_missed(conn)

    since = doses.now_utc() - timedelta(days=7)
    result = []
    for p in patients:
        agg = conn.execute(
            """
            SELECT COALESCE(sum(scheduled - pending), 0)::int AS resolved,
                   COALESCE(sum(on_time + late + early), 0)::int AS taken,
                   COALESCE(sum(on_time), 0)::int AS on_time,
                   COALESCE(sum(missed), 0)::int AS missed
            FROM daily_adherence WHERE patient_id = %s AND day >= %s
            """,
            (p["id"], since),
        ).fetchone()
        resolved = agg["resolved"]
        result.append({
            "id": p["id"],
            "name": f"{p['first_name']} {p['last_name']}",
            "surgery_date": p["surgery_date"],
            "taken_pct_7d": round(100 * agg["taken"] / resolved) if resolved else None,
            "on_time_pct_7d": round(100 * agg["on_time"] / resolved) if resolved else None,
            "missed_7d": agg["missed"],
        })
    return result


@router.get("/patients/{patient_id}/adherence")
def adherence(patient_id: int, days: int = Query(14, ge=1, le=90),
              user: User = Depends(require_provider), conn=Depends(get_conn)):
    """Daily counts from the `daily_adherence` continuous aggregate."""
    _own_patient(conn, user, patient_id)
    doses.sweep_missed(conn)
    now = doses.now_utc()
    return conn.execute(
        """
        SELECT day, scheduled, on_time, late, early, missed, too_frequent, pending
        FROM daily_adherence
        WHERE patient_id = %s AND day >= %s AND day <= %s
        ORDER BY day
        """,
        (patient_id, now - timedelta(days=days), now),
    ).fetchall()


@router.get("/patients/{patient_id}/doses")
def recent_doses(patient_id: int, days: int = Query(3, ge=1, le=30),
                 user: User = Depends(require_provider), conn=Depends(get_conn)):
    """Individual dose rows, newest first, up to now (future pending doses are left out)."""
    _own_patient(conn, user, patient_id)
    doses.sweep_missed(conn)
    now = doses.now_utc()
    rows = doses.doses_between(conn, patient_id, now - timedelta(days=days), now)
    return list(reversed(rows))
