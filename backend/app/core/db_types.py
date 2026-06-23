"""Portable column types.

These render as native PostgreSQL types when running on Postgres, but fall
back to SQLite-compatible types for local development on SQLite. This lets the
same models work against either backend without edits.

Drop-in replacements for the equivalents in ``sqlalchemy.dialects.postgresql``:
    from app.core.db_types import JSONB, UUID, ARRAY
"""
from __future__ import annotations

from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import ARRAY as _PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB
from sqlalchemy.dialects.postgresql import UUID as _PG_UUID

# JSONB on Postgres, generic JSON (stored as TEXT) on SQLite.
JSONB = JSON().with_variant(_PG_JSONB(), "postgresql")


def UUID(as_uuid: bool = True):  # noqa: N802 - mirror the postgresql name
    """Native UUID on Postgres, CHAR(32) on SQLite."""
    return Uuid(as_uuid=as_uuid).with_variant(_PG_UUID(as_uuid=as_uuid), "postgresql")


def ARRAY(item_type):  # noqa: N802 - mirror the postgresql name
    """Native ARRAY on Postgres, JSON-encoded list on SQLite."""
    return JSON().with_variant(_PG_ARRAY(item_type), "postgresql")
