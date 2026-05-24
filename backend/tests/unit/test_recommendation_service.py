import uuid
from unittest.mock import AsyncMock

import pytest

from services import recommendation_service


@pytest.mark.asyncio
async def test_generate_recommendations_persists_empty_result_on_llm_failure(monkeypatch):
    from models import async_session
    from models.user import User
    from utils.security import hash_password

    user_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
    async with async_session() as db:
        db.add(User(id=user_id, username="rec-user", password_hash=hash_password("secret123")))
        await db.commit()

    monkeypatch.setattr(
        recommendation_service,
        "retrieve_candidates",
        lambda profile, k=30, tenant_slug=None: [
            {
                "metadata": {
                    "college_name": "测试大学",
                    "major_name": "计算机科学与技术",
                    "level": "本科",
                    "city": "广州",
                    "min_rank": 10000,
                    "min_score": 610,
                    "subjects": "物理",
                    "province": "广东",
                    "source_url": "https://example.test",
                }
            }
        ],
    )
    monkeypatch.setattr(recommendation_service, "_call_llm_with_retry", AsyncMock(side_effect=TimeoutError()))

    async with async_session() as db:
        result = await recommendation_service.generate_recommendations(
            str(user_id),
            {"subjects": "物理", "completeness": "L1"},
            db,
        )

    assert result == []
