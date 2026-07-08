"""
Auth endpoints.

POST /api/v1/auth/token   - exchange username+password for a JWT
GET  /api/v1/auth/me      - verify token and return identity
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from pydantic import BaseModel

from app.core.auth import CurrentUser, authenticate_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=Token, summary="Login and get a JWT")
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=form_data.username)
    return Token(access_token=token)


@router.get("/me", summary="Get current authenticated identity")
async def me(current_user: CurrentUser) -> dict:
    return {"identity": current_user}
