"""SQLAlchemy models. Import every model here so Alembic autogenerate sees them."""
from app.models.tenant import Tenant, TenantSettings
from app.models.user import User, RefreshToken, ApiKey, CustomRole
from app.models.knowledge import KnowledgeBase
from app.models.document import Document, DocumentChunk, DocumentVersion
from app.models.chat import ChatSession, Message, MessageCitation, Memory
from app.models.analytics import AnalyticsEvent, TokenUsage
from app.models.feedback import Feedback, ReviewQueueItem
from app.models.tool import ToolDefinition
from app.models.audit import AuditLog

__all__ = [
    "Tenant", "TenantSettings",
    "User", "RefreshToken", "ApiKey", "CustomRole",
    "KnowledgeBase",
    "Document", "DocumentChunk", "DocumentVersion",
    "ChatSession", "Message", "MessageCitation", "Memory",
    "AnalyticsEvent", "TokenUsage",
    "Feedback", "ReviewQueueItem",
    "ToolDefinition",
    "AuditLog",
]
