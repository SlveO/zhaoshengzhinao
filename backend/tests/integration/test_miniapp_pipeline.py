"""Pipeline stage: Student Entry + AI Conversation — POST /enter -> chat -> verify session + events.

Integration tests use real test DB (dockerized PostgreSQL), mock only external LLM APIs.
"""

import uuid
import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import TEST_TENANT_ID


@pytest.mark.asyncio
async def test_miniapp_enter_creates_new_session(async_client, test_tenant):
    """Pipeline stage: Student Entry — POST /miniapp/enter creates ConsultSession + event."""
    resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["is_new_session"] is True
    assert body["data"]["session_id"].startswith("sess_")
    assert body["data"]["tenant_slug"] == "test"
    assert body["data"]["has_profile"] is False


@pytest.mark.asyncio
async def test_miniapp_enter_resume_existing_session(async_client, test_tenant):
    """Pipeline stage: Student Entry — POST /miniapp/enter with existing session_id resumes it."""
    # Create first
    create_resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test"},
    )
    session_id = create_resp.json()["data"]["session_id"]

    # Resume
    resume_resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test", "session_id": session_id},
    )
    assert resume_resp.status_code == 200
    body = resume_resp.json()
    assert body["data"]["is_new_session"] is False
    assert body["data"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_miniapp_enter_returns_chat_history(async_client, test_tenant):
    """Pipeline stage: AI Conversation — enter endpoint returns chat_history for resumed sessions."""
    from models import async_session
    from models.chat_message import ChatMessage

    # Create a session
    create_resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test"},
    )
    session_id = create_resp.json()["data"]["session_id"]

    # Manually insert a chat message
    async with async_session() as db:
        msg = ChatMessage(session_id=session_id, role="user", content="你好")
        db.add(msg)
        await db.commit()

    # Resume and check history
    resume_resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test", "session_id": session_id},
    )
    body = resume_resp.json()
    assert len(body["data"]["chat_history"]) == 1
    assert body["data"]["chat_history"][0]["content"] == "你好"


@pytest.mark.asyncio
async def test_student_profile_returns_data_after_session(async_client, test_tenant):
    """Pipeline stage: Profile Extraction — GET /student/profile returns profile for existing session."""
    from models import async_session
    from models.consult_session import ConsultSession

    # Create session
    create_resp = await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test"},
    )
    session_id = create_resp.json()["data"]["session_id"]

    # Update profile directly
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(ConsultSession).where(ConsultSession.session_id == session_id)
        )
        session = result.scalar_one()
        session.province = "广东"
        session.subject_type = "物理类"
        session.score = 610
        await db.commit()

    # Fetch profile
    profile_resp = await async_client.get(
        f"/api/v1/student/profile?session_id={session_id}",
    )
    assert profile_resp.status_code == 200
    data = profile_resp.json()["data"]
    assert data["has_profile"] is True
    assert data["profile"]["province"] == "广东"
    assert data["profile"]["score"] == 610


@pytest.mark.asyncio
async def test_student_profile_returns_empty_for_unknown_session(async_client, test_tenant):
    """Pipeline stage: Student Entry — GET /student/profile returns has_profile=False for unknown session."""
    resp = await async_client.get(
        "/api/v1/student/profile?session_id=sess_nonexistent",
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["has_profile"] is False


@pytest.mark.asyncio
async def test_events_written_after_enter(async_client, test_tenant):
    """Pipeline stage: Student Entry — chat_session_started event written to event_logs."""
    from models import async_session
    from sqlalchemy import text

    await async_client.post(
        "/api/v1/miniapp/enter",
        json={"tenant_slug": "test"},
    )

    async with async_session() as db:
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM event_logs "
                "WHERE tenant_id = :tid AND event_type = 'chat_session_started'"
            ),
            {"tid": TEST_TENANT_ID},
        )
        count = result.scalar()
        assert count >= 1


class TestDualModeSessionTTL:

    @pytest.mark.asyncio
    async def test_enter_without_jwt_creates_1day_ttl(self, async_client):
        resp = await async_client.post("/api/v1/miniapp/enter", json={"tenant_slug": "scnu"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_new_session"] is True
        assert data["session_id"].startswith("sess_")

        from services.consult_service import get_session
        from datetime import datetime, timedelta, timezone
        session = await get_session(data["session_id"])
        assert session is not None
        assert session.user_id is None
        now = datetime.now(timezone.utc)
        ttl = session.expires_at - now
        assert timedelta(hours=23) < ttl < timedelta(hours=25)

    @pytest.mark.asyncio
    async def test_enter_with_jwt_creates_30day_ttl(self, async_client):
        from utils.jwt import create_token
        token = create_token("11111111-1111-1111-1111-111111111111", "testuser", 60)

        resp = await async_client.post(
            "/api/v1/miniapp/enter",
            json={"tenant_slug": "scnu"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_new_session"] is True

        from services.consult_service import get_session
        from datetime import datetime, timedelta, timezone
        session = await get_session(data["session_id"])
        assert session is not None
        assert session.user_id is not None
        now = datetime.now(timezone.utc)
        ttl = session.expires_at - now
        assert timedelta(days=29) < ttl < timedelta(days=31)

    @pytest.mark.asyncio
    async def test_expired_session_returns_new(self, async_client):
        resp1 = await async_client.post("/api/v1/miniapp/enter", json={"tenant_slug": "scnu"})
        old_id = resp1.json()["data"]["session_id"]

        from services.consult_service import get_session
        from datetime import datetime, timedelta, timezone
        from models import async_session as dbs
        from sqlalchemy import update
        from models.consult_session import ConsultSession

        async with dbs() as db:
            await db.execute(
                update(ConsultSession)
                .where(ConsultSession.session_id == old_id)
                .values(expires_at=datetime.now(timezone.utc) - timedelta(hours=1))
            )
            await db.commit()

        resp2 = await async_client.post("/api/v1/miniapp/enter", json={
            "session_id": old_id, "tenant_slug": "scnu",
        })
        data2 = resp2.json()["data"]
        assert data2["is_new_session"] is True
        assert data2["session_id"] == old_id


class TestRecommendationsWithIntent:
    """推荐接口的意向方向加分 + profile API 返回 intent_majors"""

    @pytest.mark.asyncio
    async def test_student_profile_returns_intent_majors(
        self, async_client, test_tenant
    ):
        """GET /student/profile 的 profile 包含 intent_majors 字段"""
        from models import async_session
        from models.consult_session import ConsultSession
        import uuid

        async with async_session() as db:
            session = ConsultSession(
                session_id=f"sess_{uuid.uuid4().hex[:12]}",
                tenant_slug="test",
                province="广东",
                intent_majors=["计算机", "人工智能"],
            )
            db.add(session)
            await db.commit()
            sid = session.session_id

        resp = await async_client.get(
            "/api/v1/student/profile", params={"session_id": sid}
        )
        assert resp.status_code == 200
        data = resp.json().get("data")
        assert data is not None
        assert data.get("has_profile") is True
        profile = data.get("profile")
        assert profile is not None
        assert "计算机" in profile.get("intent_majors", [])
        assert "人工智能" in profile.get("intent_majors", [])

    @pytest.mark.asyncio
    async def test_recommendations_returns_intent_boost_reason(
        self, async_client, test_tenant
    ):
        """intent_majors 匹配时，推荐理由包含意向方向"""
        from models import async_session
        from models.consult_session import ConsultSession
        from models.college import College
        from models.admission import AdmissionData
        import uuid

        async with async_session() as db:
            college = College(
                id=uuid.uuid4(), name="华南师范大学", code="scnu_test",
                type="师范", level="本科", province="广东", city="广州",
            )
            db.add(college)
            await db.flush()
            db.add(AdmissionData(
                id=uuid.uuid4(), college_id=college.id,
                major_name="计算机科学与技术", year=2024,
                min_score=600, min_rank=20000, province="广东",
                batch="本科批", subject_requirements="物理+不限",
            ))
            await db.commit()

        async with async_session() as db:
            session = ConsultSession(
                session_id=f"sess_{uuid.uuid4().hex[:12]}",
                tenant_slug="test", province="广东",
                subject_type="物理类", score=620,
                intent_majors=["计算机"],
            )
            db.add(session)
            await db.commit()
            sid = session.session_id

        resp = await async_client.post(
            "/api/v1/recommendations",
            json={"session_id": sid, "tenant_slug": "test"},
        )
        assert resp.status_code == 200
        data = resp.json().get("data")
        items = data.get("items", [])
        cs_item = next((i for i in items if "计算机" in i.get("major_name", "")), None)
        assert cs_item is not None, "推荐列表应包含计算机相关专业"
        reasons = cs_item.get("reasons", [])
        assert any("意向方向" in r for r in reasons), f"推荐理由应含意向方向，实际: {reasons}"

    @pytest.mark.asyncio
    async def test_recommendations_no_intent_boost_when_empty(
        self, async_client, test_tenant
    ):
        """intent_majors 为空 → 无意向方向理由"""
        from models import async_session
        from models.consult_session import ConsultSession
        from models.college import College
        from models.admission import AdmissionData
        import uuid

        async with async_session() as db:
            college = College(
                id=uuid.uuid4(), name="华南师范大学", code="scnu_test2",
                type="师范", level="本科", province="广东", city="广州",
            )
            db.add(college)
            await db.flush()
            db.add(AdmissionData(
                id=uuid.uuid4(), college_id=college.id,
                major_name="计算机科学与技术", year=2024,
                min_score=600, min_rank=20000, province="广东",
                batch="本科批", subject_requirements="物理+不限",
            ))
            await db.commit()

        async with async_session() as db:
            session = ConsultSession(
                session_id=f"sess_{uuid.uuid4().hex[:12]}",
                tenant_slug="test", score=620, intent_majors=[],
            )
            db.add(session)
            await db.commit()
            sid = session.session_id

        resp = await async_client.post(
            "/api/v1/recommendations",
            json={"session_id": sid, "tenant_slug": "test"},
        )
        data = resp.json().get("data")
        for item in data.get("items", []):
            assert not any("意向方向" in r for r in item.get("reasons", [])), \
                f"intent_majors 为空不应出现意向方向理由"
