"""Unit tests for password hashing, JWT, token rotation hashing and encryption."""
from __future__ import annotations

import jwt
import pytest

from app.core import security


def test_password_roundtrip():
    h = security.hash_password("s3cret-pw")
    assert h != "s3cret-pw"
    assert security.verify_password("s3cret-pw", h)
    assert not security.verify_password("wrong", h)


def test_access_token_contains_claims():
    token = security.create_access_token(
        user_id="u1", tenant_id="t1", role="employee", scopes=["chat:use"]
    )
    payload = security.decode_token(token)
    assert payload["sub"] == "u1"
    assert payload["tenant_id"] == "t1"
    assert payload["type"] == security.ACCESS_TOKEN
    assert payload["scopes"] == ["chat:use"]


def test_refresh_token_has_jti():
    token, jti = security.create_refresh_token(user_id="u1", tenant_id="t1")
    payload = security.decode_token(token)
    assert payload["jti"] == jti
    assert payload["type"] == security.REFRESH_TOKEN


def test_expired_token_rejected(monkeypatch):
    import datetime

    token = jwt.encode(
        {
            "sub": "u",
            "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1),
        },
        security.settings.SECRET_KEY,
        algorithm=security.settings.JWT_ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(token)


def test_field_encryption_roundtrip():
    secret = "sk-abc123-very-secret"
    enc = security.encrypt_value(secret)
    assert enc != secret
    assert security.decrypt_value(enc) == secret


def test_api_key_hashing():
    raw, hashed = security.generate_api_key()
    assert raw.startswith("cb_")
    assert security.hash_token(raw) == hashed
