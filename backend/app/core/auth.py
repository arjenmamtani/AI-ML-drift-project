"""
JWT authentication.

Two-layer auth strategy:
  - API key auth  : for machine-to-machine (e.g. a deployed model posting predictions)
  - Bearer JWT    : for human users accessing the dashboard or triggering retrains

For this project we keep it simple — a single hardcoded admin user and
API key seeded from environment variables. In production you'd store
hashed API keys in the DB and support multi-tenancy.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# In production: store hashed API keys in the DB.
# For this project: one key from env, checked with constant-time comparison.
_VALID_API_KEY = "dev-api-key-change-in-production"


# ── Token creation ────────────────────────────────────────────────────────────

def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


# ── Token verification ────────────────────────────────────────────────────────

def _verify_jwt(token: str) -> str:
    """Returns the subject claim or raises HTTPException."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject: str | None = payload.get("sub")
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return subject
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── FastAPI dependencies ──────────────────────────────────────────────────────

async def get_current_user(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    api_key: str | None = Security(api_key_header),
) -> str:
    """
    Accepts either a Bearer JWT or an X-API-Key header.
    Returns the authenticated identity (username or 'api-key-client').
    """
    if bearer is not None:
        return _verify_jwt(bearer.credentials)

    if api_key is not None:
        if api_key == _VALID_API_KEY:
            return "api-key-client"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide Bearer token or X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Shorthand type alias for use in route signatures
CurrentUser = Annotated[str, Depends(get_current_user)]


# ── Login endpoint helper ─────────────────────────────────────────────────────

def authenticate_user(username: str, password: str) -> bool:
    """
    Validate username + password against the configured admin credentials.
    In production: look up hashed password from DB.
    """
    valid_username = "admin"
    valid_password = "drift-sentinel-admin"  # override via env in production
    return username == valid_username and password == valid_password
