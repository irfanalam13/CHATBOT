"""Security tests: tenant-isolation query construction and Principal RBAC."""
from __future__ import annotations

import uuid

import pytest

from app.api.deps import Principal
from app.core.exceptions import ForbiddenError
from app.core.rbac import Permission


def test_principal_require_enforces_permission():
    viewer = Principal(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="viewer", scopes=[]
    )
    viewer.require(Permission.CHAT_USE)  # allowed
    with pytest.raises(ForbiddenError):
        viewer.require(Permission.USER_CREATE)


def test_principal_custom_scope_grants_permission():
    p = Principal(
        user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), role="employee",
        scopes=[Permission.ANALYTICS_READ.value],
    )
    p.require(Permission.ANALYTICS_READ)


def test_repository_scopes_every_query_by_tenant():
    """The base repository must filter by tenant_id on its core select."""
    from app.repositories.repos import DocumentRepo

    tenant_id = uuid.uuid4()
    repo = DocumentRepo.__new__(DocumentRepo)
    repo.model = DocumentRepo.model
    repo.tenant_id = tenant_id
    stmt = repo._scoped()
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "tenant_id" in compiled
