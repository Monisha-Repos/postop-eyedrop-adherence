
"""Provider endpoints for the EyeSpy AI doctor dashboard.

Every patient request is scoped to the signed-in provider.
Includes:
- Patient list
- Medication adherence
- Recent doses
- Eye-photo history
- Protected eye-photo retrieval
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .. import doses
from ..auth import User, require_provider
from ..db import get_conn


router = APIRouter(prefix="/provider", tags=["provider"])


def _own_patient(conn, user: User, patient_id: int) -> dict:
    """Verify that this patient belongs to the signed-in doctor."""

    row = conn.execute(
        """
        SELECT
            id,
            first_name,
            last_name,
            timezone,
            surgery_date
        FROM patients
        WHERE id = %s
          AND provider_id = %s
        """,
        (patient_id, user.id),
    ).fetchone()

    if not row:
        # Return 404 instead of revealing another provider's patient.
        raise HTTPException(404, "Patient not found")

    doses.ensure_doses(conn, row["id"], row["timezone"])
    return row


@router.get("/patients")
def list_patients(
    user: User = Depends(require_provider),
    conn=Depends(get_conn),
):
    """List patients assigned to the signed-in doctor."""

    patients = conn.execute(
        """
        SELECT
            id,
            first_name,
            last_name,
            timezone,
            surgery_date
        FROM patients
        WHERE provider_id = %s
        ORDER BY last_name
        """,
        (user.id,),
    ).fetchall()

    for patient in patients:
        doses.ensure_doses(
            conn,
            patient["id"],
            patient["timezone"],
        )

    doses.sweep_missed(conn)

    since = doses.now_utc() - timedelta(days=7)
    result = []

    for patient in patients:
        agg = conn.execute(
            """
            SELECT
                COALESCE(
                    SUM(scheduled - pending), 0
                )::int AS resolved,
                COALESCE(
                    SUM(on_time + late + early), 0
                )::int AS taken,
                COALESCE(
                    SUM(on_time), 0
                )::int AS on_time,
                COALESCE(
                    SUM(missed), 0
                )::int AS missed
            FROM daily_adherence
            WHERE patient_id = %s
              AND day >= %s
            """,
            (patient["id"], since),
        ).fetchone()

        resolved = agg["resolved"]

        result.append(
            {
                "id": patient["id"],
                "name": (
                    f"{patient['first_name']} "
                    f"{patient['last_name']}"
                ),
                "surgery_date": patient["surgery_date"],
                "taken_pct_7d": (
                    round(100 * agg["taken"] / resolved)
                    if resolved
                    else None
                ),
                "on_time_pct_7d": (
                    round(100 * agg["on_time"] / resolved)
                    if resolved
                    else None
                ),
                "missed_7d": agg["missed"],
            }
        )

    return result


@router.get("/patients/{patient_id}/adherence")
def adherence(
    patient_id: int,
    days: int = Query(14, ge=1, le=90),
    user: User = Depends(require_provider),
    conn=Depends(get_conn),
):
    """Return daily medication adherence for one patient."""

    _own_patient(conn, user, patient_id)
    doses.sweep_missed(conn)

    now = doses.now_utc()

    return conn.execute(
        """
        SELECT
            day,
            scheduled,
            on_time,
            late,
            early,
            missed,
            too_frequent,
            pending
        FROM daily_adherence
        WHERE patient_id = %s
          AND day >= %s
          AND day <= %s
        ORDER BY day
        """,
        (
            patient_id,
            now - timedelta(days=days),
            now,
        ),
    ).fetchall()


@router.get("/patients/{patient_id}/doses")
def recent_doses(
    patient_id: int,
    days: int = Query(3, ge=1, le=30),
    user: User = Depends(require_provider),
    conn=Depends(get_conn),
):
    """Return recent individual medication doses."""

    _own_patient(conn, user, patient_id)
    doses.sweep_missed(conn)

    now = doses.now_utc()

    rows = doses.doses_between(
        conn,
        patient_id,
        now - timedelta(days=days),
        now,
    )

    return list(reversed(rows))


@router.get("/patients/{patient_id}/eye-analyses")
def patient_eye_analyses(
    patient_id: int,
    user: User = Depends(require_provider),
    conn=Depends(get_conn),
):
    """List saved eye analyses for a patient assigned to this doctor."""

    _own_patient(conn, user, patient_id)

    rows = conn.execute(
        """
        SELECT
            id,
            analysis,
            created_at,
            image_data IS NOT NULL AS has_image
        FROM eye_analyses
        WHERE patient_id = %s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (patient_id,),
    ).fetchall()

    return [dict(row) for row in rows]


@router.get(
    "/patients/{patient_id}/eye-analyses/{analysis_id}/image"
)
def patient_eye_analysis_image(
    patient_id: int,
    analysis_id: int,
    user: User = Depends(require_provider),
    conn=Depends(get_conn),
):
    """Return a stored eye photo for the assigned doctor only."""

    _own_patient(conn, user, patient_id)

    row = conn.execute(
        """
        SELECT
            image_data,
            image_type
        FROM eye_analyses
        WHERE id = %s
          AND patient_id = %s
        """,
        (
            analysis_id,
            patient_id,
        ),
    ).fetchone()

    if not row or row["image_data"] is None:
        raise HTTPException(
            status_code=404,
            detail="Eye photo not found",
        )

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    image_type = row["image_type"]

    if image_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail="Unsupported image format",
        )

    return Response(
        content=bytes(row["image_data"]),
        media_type=image_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
