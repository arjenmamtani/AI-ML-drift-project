"""
Unit tests for JWT authentication.
"""

import pytest
from fastapi import HTTPException

from app.core.auth import (
    authenticate_user,
    create_access_token,
    _verify_jwt,
)
from app.core.config import settings


class TestTokenCreation:
    def test_creates_valid_token(self):
        token = create_access_token("testuser")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_decodes_correctly(self):
        token = create_access_token("testuser")
        subject = _verify_jwt(token)
        assert subject == "testuser"

    def test_tampered_token_raises(self):
        token = create_access_token("testuser")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException) as exc_info:
            _verify_jwt(tampered)
        assert exc_info.value.status_code == 401

    def test_garbage_token_raises(self):
        with pytest.raises(HTTPException) as exc_info:
            _verify_jwt("not.a.real.token")
        assert exc_info.value.status_code == 401


class TestAuthentication:
    def test_valid_credentials_pass(self):
        assert authenticate_user("admin", "drift-sentinel-admin") is True

    def test_wrong_password_fails(self):
        assert authenticate_user("admin", "wrongpassword") is False

    def test_wrong_username_fails(self):
        assert authenticate_user("hacker", "drift-sentinel-admin") is False

    def test_empty_credentials_fail(self):
        assert authenticate_user("", "") is False
