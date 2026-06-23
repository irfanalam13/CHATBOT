"""Password hashing, JWT issue/verify, refresh-token rotation, field encryption."""
from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"


# ── Passwords ──────────────────────────────────────────────────
# Use the bcrypt library directly (passlib is unmaintained and breaks with
# bcrypt >= 5). bcrypt only considers the first 72 bytes, so truncate explicitly.
def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── JWT ────────────────────────────────────────────────────────
def _encode(payload: dict[str, Any], expires: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        **payload,
        "iat": now,
        "exp": now + expires,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    *, user_id: str, tenant_id: str, role: str, scopes: list[str] | None = None
) -> str:
    return _encode(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "scopes": scopes or [],
        },
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        ACCESS_TOKEN,
    )


def create_refresh_token(*, user_id: str, tenant_id: str) -> tuple[str, str]:
    """Return (jwt, jti). The jti is persisted so the token can be rotated/revoked."""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": user_id,
            "tenant_id": tenant_id,
            "type": REFRESH_TOKEN,
            "jti": jti,
            "iat": now,
            "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        },
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError on any problem."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def hash_token(token: str) -> str:
    """One-way hash for storing refresh tokens at rest."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Return (plaintext_key, sha256_hash) for tenant programmatic access."""
    raw = "cb_" + secrets.token_urlsafe(32)
    return raw, hash_token(raw)


# ── Field-level encryption (tenant secrets, provider keys) ─────
def _fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    # Derive a valid 32-byte urlsafe-base64 key from arbitrary input.
    digest = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_value(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()
