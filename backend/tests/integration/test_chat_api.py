import pytest


@pytest.mark.asyncio
async def test_chat_session_create_and_read(async_client, test_tenant):
    created = await async_client.post("/api/v1/chat/session", headers={"X-Tenant": "test"})

    assert created.status_code == 200
    body = created.json()
    assert body["session_id"]
    assert body["guest"] is True

    fetched = await async_client.get(f"/api/v1/chat/session/{body['session_id']}", headers={"X-Tenant": "test"})
    assert fetched.status_code == 200
    assert fetched.json()["session_id"] == body["session_id"]

    deleted = await async_client.delete(f"/api/v1/chat/session/{body['session_id']}", headers={"X-Tenant": "test"})
    assert deleted.status_code == 200
