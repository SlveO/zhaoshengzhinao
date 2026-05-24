import pytest


@pytest.mark.asyncio
async def test_register_login_refresh_flow(async_client):
    register = await async_client.post(
        "/api/v1/auth/register",
        json={
            "username": "api-user",
            "password": "secret123",
            "region": "广东",
            "score": 610,
            "subjects": "物理 化学",
        },
    )
    assert register.status_code == 200
    tokens = register.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "api-user", "password": "secret123"},
    )
    assert login.status_code == 200

    refresh = await async_client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]
