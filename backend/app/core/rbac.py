"""Role-Based Access Control: roles, permissions and the permission matrix."""
from __future__ import annotations

import enum


class Role(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    VIEWER = "viewer"


class Permission(str, enum.Enum):
    # Tenant
    TENANT_MANAGE = "tenant:manage"
    TENANT_READ = "tenant:read"
    # Users
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    # Knowledge base / documents
    KB_MANAGE = "kb:manage"
    KB_READ = "kb:read"
    DOC_UPLOAD = "doc:upload"
    DOC_READ = "doc:read"
    DOC_DELETE = "doc:delete"
    # Chat
    CHAT_USE = "chat:use"
    CHAT_READ_ALL = "chat:read_all"   # read other users' sessions in the tenant
    # Search
    SEARCH_USE = "search:use"
    # Analytics / feedback
    ANALYTICS_READ = "analytics:read"
    FEEDBACK_REVIEW = "feedback:review"
    # Tools / settings / admin
    TOOL_MANAGE = "tool:manage"
    SETTINGS_MANAGE = "settings:manage"
    ADMIN_PLATFORM = "admin:platform"   # super-admin only


# Permission matrix — what each built-in role can do.
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # everything
    Role.TENANT_ADMIN: {
        Permission.TENANT_READ,
        Permission.USER_CREATE, Permission.USER_READ,
        Permission.USER_UPDATE, Permission.USER_DELETE,
        Permission.KB_MANAGE, Permission.KB_READ,
        Permission.DOC_UPLOAD, Permission.DOC_READ, Permission.DOC_DELETE,
        Permission.CHAT_USE, Permission.CHAT_READ_ALL,
        Permission.SEARCH_USE,
        Permission.ANALYTICS_READ, Permission.FEEDBACK_REVIEW,
        Permission.TOOL_MANAGE, Permission.SETTINGS_MANAGE,
    },
    Role.MANAGER: {
        Permission.TENANT_READ,
        Permission.USER_READ,
        Permission.KB_READ,
        Permission.DOC_UPLOAD, Permission.DOC_READ, Permission.DOC_DELETE,
        Permission.CHAT_USE, Permission.CHAT_READ_ALL,
        Permission.SEARCH_USE,
        Permission.ANALYTICS_READ, Permission.FEEDBACK_REVIEW,
    },
    Role.EMPLOYEE: {
        Permission.KB_READ,
        Permission.DOC_UPLOAD, Permission.DOC_READ,
        Permission.CHAT_USE,
        Permission.SEARCH_USE,
    },
    Role.VIEWER: {
        Permission.KB_READ,
        Permission.DOC_READ,
        Permission.CHAT_USE,
        Permission.SEARCH_USE,
    },
}


def permissions_for(role: str, custom: set[str] | None = None) -> set[Permission]:
    """Resolve effective permissions for a role plus any custom grants."""
    try:
        base = set(ROLE_PERMISSIONS[Role(role)])
    except ValueError:
        base = set()
    if custom:
        for c in custom:
            try:
                base.add(Permission(c))
            except ValueError:
                continue
    return base


def has_permission(role: str, permission: Permission, custom: set[str] | None = None) -> bool:
    return permission in permissions_for(role, custom)
