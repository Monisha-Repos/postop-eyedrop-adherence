"""Auth0 access-token validation and role checks, plus dock token checks.

A request is allowed only when BOTH are true:
  * the Auth0 token carries the role (custom claim added by an Auth0 Action), and
  * a matching patients/providers row exists for the token's `sub`.
So providers only ever see their own patients, and patients only themselves.
"""
import hashlib
import logging
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException

from . import config
from .db import get_conn

log = logging.getLogger(__name__)

_jwks_client: jwt.PyJWKClient | None = None


@dataclass
class User:
    sub: str
    role: str  # patient | provider
    id: int    # patients.id or providers.id
    name: str


def _decode(token: str) -> tuple[str, list[str] | None]:
    """Returns (sub, roles). roles is None for dev tokens (role comes from the database)."""
    if config.DEV_AUTH_BYPASS and token.startswith("dev:"):
        return token[4:], None

    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"https://{config.AUTH0_DOMAIN}/.well-known/jwks.json")
    try:
        key = _jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=config.AUTH0_AUDIENCE,
            issuer=f"https://{config.AUTH0_DOMAIN}/",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"Invalid token: {exc}")
    return claims["sub"], list(claims.get(config.AUTH0_ROLES_CLAIM, []))


def current_user(authorization: str = Header(default=""), conn=Depends(get_conn)) -> User:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Missing bearer token")
    sub, roles = _decode(token)

    if roles is None or "provider" in roles:
        row = conn.execute("SELECT id, name FROM providers WHERE auth0_sub = %s", (sub,)).fetchone()
        if row:
            return User(sub, "provider", row["id"], row["name"])
    if roles is None or "patient" in roles:
        row = conn.execute("SELECT id, first_name FROM patients WHERE auth0_sub = %s", (sub,)).fetchone()
        if row:
            return User(sub, "patient", row["id"], row["first_name"])
    raise HTTPException(403, "No Eye Spy account with a matching role for this login")


def require_patient(user: User = Depends(current_user)) -> User:
    if user.role != "patient":
        raise HTTPException(403, "Patients only")
    return user


def require_provider(user: User = Depends(current_user)) -> User:
    if user.role != "provider":
        raise HTTPException(403, "Providers only")
    return user


def hash_device_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_device(x_device_token: str = Header(default=""), conn=Depends(get_conn)) -> dict:
    if not x_device_token:
        raise HTTPException(401, "Missing X-Device-Token")
    row = conn.execute(
        """
        SELECT d.id, d.patient_id, p.timezone
        FROM devices d JOIN patients p ON p.id = d.patient_id
        WHERE d.token_sha256 = %s
        """,
        (hash_device_token(x_device_token),),
    ).fetchone()
    if not row:
        raise HTTPException(401, "Unknown device")
    return row
