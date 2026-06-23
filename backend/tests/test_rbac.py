"""RBAC permission-matrix tests."""
from __future__ import annotations

from app.core.rbac import Permission, Role, has_permission, permissions_for


def test_super_admin_has_everything():
    assert has_permission(Role.SUPER_ADMIN.value, Permission.ADMIN_PLATFORM)
    assert has_permission(Role.SUPER_ADMIN.value, Permission.CHAT_USE)


def test_viewer_is_read_only():
    assert has_permission(Role.VIEWER.value, Permission.DOC_READ)
    assert not has_permission(Role.VIEWER.value, Permission.DOC_UPLOAD)
    assert not has_permission(Role.VIEWER.value, Permission.USER_CREATE)


def test_employee_cannot_manage_users():
    assert has_permission(Role.EMPLOYEE.value, Permission.CHAT_USE)
    assert not has_permission(Role.EMPLOYEE.value, Permission.USER_CREATE)
    assert not has_permission(Role.EMPLOYEE.value, Permission.ANALYTICS_READ)


def test_custom_permission_grant():
    assert not has_permission(Role.EMPLOYEE.value, Permission.ANALYTICS_READ)
    assert has_permission(
        Role.EMPLOYEE.value, Permission.ANALYTICS_READ, {Permission.ANALYTICS_READ.value}
    )


def test_unknown_role_has_no_permissions():
    assert permissions_for("nonexistent") == set()
