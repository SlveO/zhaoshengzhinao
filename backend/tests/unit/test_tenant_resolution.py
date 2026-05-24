import pytest

from tenants.service import resolve_tenant, update_tenant_config


@pytest.mark.asyncio
async def test_resolve_tenant_by_slug(test_tenant):
    tenant = await resolve_tenant("test")

    assert tenant is not None
    assert tenant.slug == "test"


@pytest.mark.asyncio
async def test_update_tenant_config_deep_merges(test_tenant):
    updated = await update_tenant_config(
        test_tenant,
        {"brand": {"welcome_text": "hello"}, "modules": {"funnel": False}},
    )

    assert updated.config["brand"]["name"] == "Test University"
    assert updated.config["brand"]["welcome_text"] == "hello"
    assert updated.config["modules"]["funnel"] is False
    assert updated.config["modules"]["profile_dashboard"] is True
