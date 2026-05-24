import json

import pytest

from services import chat_service


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)


@pytest.mark.asyncio
async def test_chat_session_create_get_save_delete(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(chat_service, "redis", fake_redis)

    session_id = await chat_service.create_session(
        "33333333-3333-3333-3333-333333333333",
        {"score": 610},
    )

    state = await chat_service.get_dialog_state(session_id)
    assert state["session_id"] == session_id
    assert state["slots"]["score"] == 610

    state["messages"].append({"role": "user", "content": "我喜欢计算机"})
    await chat_service.save_dialog_state(session_id, state)
    saved = json.loads(fake_redis.store[f"dialog:{session_id}"])
    assert saved["messages"][0]["content"] == "我喜欢计算机"

    await chat_service.delete_dialog_state(session_id)
    assert await chat_service.get_dialog_state(session_id) is None
