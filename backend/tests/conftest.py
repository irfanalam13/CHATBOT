"""Shared test fixtures and env defaults (no external services required)."""
from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("ENVIRONMENT", "development")
