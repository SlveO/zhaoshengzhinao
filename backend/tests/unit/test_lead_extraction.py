"""Pipeline stage: Lead & Consultation Management — lead data extraction from event_logs + consult_sessions."""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


async def extract_leads(tenant_id: uuid.UUID) -> list[dict]:
    """Extract lead records by joining event_logs with consult_sessions.

    Pipeline stage: Lead Management — data source: event_logs + consult_sessions.
    """
    from models import async_session
    from sqlalchemy import text

    async with async_session() as db:
        result = await db.execute(
            text("""
                SELECT DISTINCT ON (cs.session_id)
                    cs.session_id,
                    cs.province,
                    cs.subject_type,
                    cs.score,
                    cs.intent_majors,
                    cs.consult_stage,
                    cs.created_at as session_created,
                    cs.updated_at as session_updated,
                    COUNT(el.id) OVER (PARTITION BY cs.session_id) as event_count,
                    MAX(el.created_at) OVER (PARTITION BY cs.session_id) as last_event_at
                FROM consult_sessions cs
                LEFT JOIN event_logs el ON el.session_id::text = cs.session_id
                WHERE cs.tenant_slug = (
                    SELECT slug FROM tenants WHERE id = :tid
                )
                ORDER BY cs.session_id, el.created_at DESC
            """),
            {"tid": tenant_id},
        )
        rows = result.fetchall()
        return [
            {
                "session_id": row.session_id,
                "province": row.province,
                "subject_type": row.subject_type,
                "score": row.score,
                "intent_majors": row.intent_majors,
                "consult_stage": row.consult_stage,
                "session_created": row.session_created.isoformat() if row.session_created else None,
                "session_updated": row.session_updated.isoformat() if row.session_updated else None,
                "event_count": row.event_count,
                "last_event_at": row.last_event_at.isoformat() if row.last_event_at else None,
            }
            for row in rows
        ]


class TestLeadExtraction:
    """Pipeline stage: Lead Management — extracting actionable lead records from raw data."""

    @pytest.mark.asyncio
    async def test_extract_leads_empty_when_no_sessions(self):
        """Returns empty list when no consult_sessions exist for the tenant."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("models.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            leads = await extract_leads(uuid.uuid4())
            assert leads == []

    @pytest.mark.asyncio
    async def test_extract_leads_includes_profile_fields(self):
        """Lead records include province, subject_type, score from consult_sessions."""
        now = datetime.now(timezone.utc)
        mock_row = MagicMock()
        mock_row.session_id = "sess_lead1"
        mock_row.province = "广东"
        mock_row.subject_type = "物理类"
        mock_row.score = 610
        mock_row.intent_majors = ["计算机"]
        mock_row.consult_stage = "focus"
        mock_row.session_created = now
        mock_row.session_updated = now
        mock_row.event_count = 5
        mock_row.last_event_at = now

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("models.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            leads = await extract_leads(uuid.uuid4())
            assert len(leads) == 1
            lead = leads[0]
            assert lead["province"] == "广东"
            assert lead["subject_type"] == "物理类"
            assert lead["score"] == 610
            assert lead["consult_stage"] == "focus"

    @pytest.mark.asyncio
    async def test_extract_leads_includes_event_stats(self):
        """Lead records include event_count and last_event_at from event_logs join."""
        now = datetime.now(timezone.utc)
        mock_row = MagicMock()
        mock_row.session_id = "sess_lead2"
        mock_row.province = ""
        mock_row.subject_type = ""
        mock_row.score = 0
        mock_row.intent_majors = []
        mock_row.consult_stage = "new"
        mock_row.session_created = now
        mock_row.session_updated = now
        mock_row.event_count = 12
        mock_row.last_event_at = now

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("models.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            leads = await extract_leads(uuid.uuid4())
            assert len(leads) == 1
            assert leads[0]["event_count"] == 12
            assert leads[0]["last_event_at"] is not None

    @pytest.mark.asyncio
    async def test_extract_leads_handles_null_last_event(self):
        """Lead with no events still returns with event_count=0 and null last_event_at."""
        now = datetime.now(timezone.utc)
        mock_row = MagicMock()
        mock_row.session_id = "sess_noevents"
        mock_row.province = "北京"
        mock_row.subject_type = "历史类"
        mock_row.score = 580
        mock_row.intent_majors = []
        mock_row.consult_stage = "open"
        mock_row.session_created = now
        mock_row.session_updated = now
        mock_row.event_count = 0
        mock_row.last_event_at = None

        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("models.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            leads = await extract_leads(uuid.uuid4())
            assert len(leads) == 1
            assert leads[0]["event_count"] == 0
            assert leads[0]["last_event_at"] is None

    @pytest.mark.asyncio
    async def test_extract_leads_respects_tenant_isolation(self):
        """extract_leads query filters by tenant_slug, only returning that tenant's leads."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("models.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            tenant_a_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
            leads = await extract_leads(tenant_a_id)

            # Verify the query was called with the correct tenant_id
            call_args = mock_db.execute.call_args
            params = call_args[0][1]
            assert params["tid"] == tenant_a_id
