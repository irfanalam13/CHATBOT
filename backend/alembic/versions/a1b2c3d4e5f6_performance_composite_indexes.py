"""performance: composite indexes for hot query paths

Adds composite indexes matching the multi-column filters/sorts the application
actually issues, so Postgres can satisfy them with a single index range scan
instead of a single-column index plus a filter/sort step:

* messages          (session_id, created_at)        — transcript / history reads
* chat_sessions     (tenant_id, user_id, status)     — session list endpoint
* memories          (tenant_id, scope, owner_id)     — memory relevance lookup
* analytics_events  (tenant_id, event_type, created_at) and (tenant_id, created_at)
* token_usage       (tenant_id, created_at)          — cost/usage rollups

Revision ID: a1b2c3d4e5f6
Revises: 0fde65a5a330
Create Date: 2026-06-23 23:59:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0fde65a5a330"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_messages_session_created", "messages", ["session_id", "created_at"]
    )
    op.create_index(
        "ix_chat_sessions_tenant_user_status",
        "chat_sessions",
        ["tenant_id", "user_id", "status"],
    )
    op.create_index(
        "ix_memories_tenant_scope_owner",
        "memories",
        ["tenant_id", "scope", "owner_id"],
    )
    op.create_index(
        "ix_analytics_tenant_type_created",
        "analytics_events",
        ["tenant_id", "event_type", "created_at"],
    )
    op.create_index(
        "ix_analytics_tenant_created",
        "analytics_events",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_token_usage_tenant_created",
        "token_usage",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_token_usage_tenant_created", table_name="token_usage")
    op.drop_index("ix_analytics_tenant_created", table_name="analytics_events")
    op.drop_index("ix_analytics_tenant_type_created", table_name="analytics_events")
    op.drop_index("ix_memories_tenant_scope_owner", table_name="memories")
    op.drop_index("ix_chat_sessions_tenant_user_status", table_name="chat_sessions")
    op.drop_index("ix_messages_session_created", table_name="messages")
