import pytest

from services.auth_service import authenticate_user, generate_tokens, register_user
from utils.jwt import decode_token


@pytest.mark.asyncio
async def test_register_and_authenticate_user():
    from models import async_session

    async with async_session() as db:
        user = await register_user(db, "student1", "secret123", "广东", 600, "物理 化学")
        assert user is not None

        duplicate = await register_user(db, "student1", "secret123", "广东", 600, "物理 化学")
        assert duplicate is None

        info = await authenticate_user(db, "student1", "secret123")
        assert info["username"] == "student1"
        assert info["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_authenticate_user_rejects_wrong_password():
    from models import async_session

    async with async_session() as db:
        await register_user(db, "student2", "secret123", "", 0, "")
        assert await authenticate_user(db, "student2", "bad-password") is None


def test_generate_tokens_are_decodable():
    tokens = generate_tokens("33333333-3333-3333-3333-333333333333", "admin")

    access_payload = decode_token(tokens["access_token"])
    refresh_payload = decode_token(tokens["refresh_token"])

    assert access_payload["user_id"] == "33333333-3333-3333-3333-333333333333"
    assert refresh_payload["username"] == "admin"
