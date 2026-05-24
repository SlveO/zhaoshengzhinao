import uuid

import pytest


@pytest.mark.asyncio
async def test_knowledge_documents_are_tenant_scoped(async_client, test_tenant, other_tenant):
    from models import async_session
    from tenants.models import TenantData

    async def seed():
        async with async_session() as db:
            db.add(
                TenantData(
                    id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                    tenant_id=test_tenant.id,
                    data_type="admission_score",
                    title="Test Tenant Doc",
                    content={"major_name": "计算机科学与技术"},
                )
            )
            db.add(
                TenantData(
                    id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
                    tenant_id=other_tenant.id,
                    data_type="admission_score",
                    title="Other Tenant Doc",
                    content={"major_name": "软件工程"},
                )
            )
            await db.commit()

    await seed()

    response = await async_client.get("/api/v1/admin/knowledge/documents", headers={"X-Tenant": "test"})

    assert response.status_code == 200
    titles = [doc["title"] for doc in response.json()["documents"]]
    assert titles == ["Test Tenant Doc"]
