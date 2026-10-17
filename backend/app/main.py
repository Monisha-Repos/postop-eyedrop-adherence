
"""Eye Spy backend.

Run from backend/:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import json
from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    File,
    UploadFile,
    HTTPException,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from google.genai import types

from . import config
from .auth import User, current_user
from .db import get_conn, pool
from .routes import device, patient, provider

# Import your existing Gemini client
from gemini_service import client

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("eyespy")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if config.DEV_AUTH_BYPASS:
        log.warning(
            "DEV_AUTH_BYPASS is ON: "
            "'Bearer dev:<sub>' tokens are accepted. "
            "Local demos only."
        )

    missing = [
        name
        for name in ("DATABASE_URL",)
        if not getattr(config, name)
    ]

    if not config.DEV_AUTH_BYPASS:
        missing += [
            name
            for name in ("AUTH0_DOMAIN", "AUTH0_AUDIENCE")
            if not getattr(config, name)
        ]

    if missing:
        raise RuntimeError(
            f"Missing in backend/.env: {', '.join(missing)}"
        )

    pool.open()
    yield
    pool.close()


app = FastAPI(
    title="Eye Spy API",
    lifespan=lifespan
)

# React frontend CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "PATCH", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Existing teammate routes
app.include_router(device.router)
app.include_router(patient.router)
app.include_router(provider.router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/me")
def me(
    user: User = Depends(current_user),
    conn=Depends(get_conn)
):
    """Tells the app which view to show."""

    body = {
        "role": user.role,
        "name": user.name,
        "humor_level": None
    }

    if user.role == "patient":
        row = conn.execute(
            "SELECT humor_level FROM patients WHERE id = %s",
            (user.id,)
        ).fetchone()

        body["humor_level"] = row["humor_level"]

    return body


# ============================================
# GEMINI AI EYE IMAGE ANALYSIS
# ============================================

MAX_IMAGE_BYTES = 5 * 1024 * 1024

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def analyze_eye_with_gemini(image_bytes, mime_type):
    """Send an eye image to Gemini for visual analysis."""

    prompt = """
    You are the visual analysis assistant for
    EyeSpy AI, an educational eye-health prototype.

    Examine the uploaded image and describe
    visible eye features.

    Assess:
    1. Visible redness
    2. Visible irritation or discharge
    3. Visible cloudiness
    4. Image quality
    5. Other notable visible observations

    Do not diagnose diseases or claim to
    detect cataracts, conjunctivitis, or infections.

    Do not claim that a normal-looking image
    means the eye is healthy.

    Return a valid JSON object with these fields:

    {
      "redness": "description",
      "irritation": "description",
      "cloudiness": "description",
      "image_quality": "description",
      "summary": "description",
      "recommendation": "description"
    }

    If the image is blurry, obstructed, or
    unsuitable, explain the limitation.

    Recommend professional evaluation for
    concerning findings.

    Eye pain, sudden vision changes, or
    vision loss require urgent medical attention.

    Do not invent observations.
    """

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            prompt,
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type
            )
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    return json.loads(response.text)


@app.post("/analyze-eye")
async def analyze_eye(
    image: UploadFile = File(...),
    user: User = Depends(current_user),
    conn=Depends(get_conn),
):
    """Analyze an eye image and save the result for the patient."""

    if user.role != "patient":
        raise HTTPException(
            status_code=403,
            detail="Only patients can save eye analyses"
        )

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG, PNG, and WebP images are allowed"
        )

    try:
        image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    finally:
        await image.close()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty"
        )

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Image must be smaller than 5 MB"
        )

    try:
        result = await run_in_threadpool(
            analyze_eye_with_gemini,
            image_bytes,
            image.content_type
        )
    except Exception:
        log.exception("Gemini eye analysis failed")
        raise HTTPException(
            status_code=502,
            detail="Eye analysis service unavailable"
        )

    try:
        # Save only the analysis text, not the uploaded photo.
        row = conn.execute(
            """
            INSERT INTO eye_analyses (
                patient_id,
                analysis,
                image_data,
                image_type
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (
                user.id,
                json.dumps(result) if isinstance(result, dict) else result,
                image_bytes,
                image.content_type
            )
        ).fetchone()
    

    except Exception:
        log.exception("Saving eye analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Could not save eye analysis"
        )

    return {
        "success": True,
        "id": row["id"],
        "created_at": row["created_at"].isoformat(),
        "analysis": result,
        "disclaimer": (
            "EyeSpy AI is an educational prototype, "
            "not a medical diagnostic tool."
        )
    }

# ============================================
# EYE ANALYSIS HISTORY
# ============================================

@app.get("/eye-analysis-history")
def get_eye_analysis_history(
    user: User = Depends(current_user),
    conn=Depends(get_conn),
):
    """Get the signed-in patient's previous eye analyses."""

    if user.role != "patient":
        raise HTTPException(
            status_code=403,
            detail="Only patients can view eye analysis history"
        )

    rows = conn.execute(
        """
        SELECT id, analysis, created_at
        FROM eye_analyses
        WHERE patient_id = %s
        ORDER BY created_at DESC, id DESC
        LIMIT 50
        """,
        (user.id,)
    ).fetchall()

    history = []

    for row in rows:
        analysis = row["analysis"]

        try:
            analysis = json.loads(analysis)
        except (json.JSONDecodeError, TypeError):
            pass

        history.append({
            "id": row["id"],
            "analysis": analysis,
            "created_at": row["created_at"].isoformat()
        })

    return {
        "success": True,
        "history": history
    }