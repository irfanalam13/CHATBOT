"""Seed a demo tenant + super-admin + sample knowledge base."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running directly (`python scripts/seed.py`) by putting the backend
# root on sys.path so the `app` package is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import AsyncSessionLocal
from app.core.rbac import Role
from app.core.security import hash_password
from app.models.knowledge import KnowledgeBase
from app.models.tenant import Tenant, TenantSettings, TenantStatus
from app.models.user import User
from app.repositories.repos import get_tenant_by_slug


async def main() -> None:
    async with AsyncSessionLocal() as db:
        if await get_tenant_by_slug(db, "demo"):
            print("Demo tenant already exists.")
            return

        tenant = Tenant(
            name="Demo Corp", slug="demo", status=TenantStatus.ACTIVE,
            vector_collection="tenant_demo",
        )
        db.add(tenant)
        await db.flush()

        db.add(TenantSettings(tenant_id=tenant.id))
        db.add(
            User(
                tenant_id=tenant.id, email="admin@demo.test",
                full_name="Demo Admin", hashed_password=hash_password("demo12345"),
                role=Role.SUPER_ADMIN.value,
            )
        )
        db.add(
            KnowledgeBase(
                tenant_id=tenant.id, name="General", slug="general",
                description="Default knowledge base",
            )
        )
        await db.commit()
        print("✓ Seeded tenant 'demo' / admin@demo.test / demo12345 (super_admin)")


if __name__ == "__main__":
    asyncio.run(main())
