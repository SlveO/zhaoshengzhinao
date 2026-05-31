"""Pipeline stage: Event Logging — write_event inserts, handles missing fields, fire-and-forget safety."""

import uuid
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.event_writer import write_event


class TestWriteEvent:
    """Pipeline stage: Event Logging (cross-cutting) — event_logs row insertion."""

    @pytest.mark.asyncio
    async def test_write_event_inserts_row_with_all_fields(self):
        """write_event with full fields inserts a complete event_logs row."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        payload = {"key": "value"}

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch("core.event_writer.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await write_event(
                tenant_id=tenant_id,
                event_type="test.event",
                user_id=user_id,
                session_id=session_id,
                payload=payload,
            )

            mock_db.execute.assert_called_once()
            mock_db.commit.assert_called_once()

            call_args = mock_db.execute.call_args
            params = call_args[0][1]
            assert params["tenant_id"] == tenant_id
            assert params["event_type"] == "test.event"
            assert params["user_id"] == user_id
            assert params["session_id"] == session_id
            assert "key" in params["payload"]

    @pytest.mark.asyncio
    async def test_write_event_handles_none_user_id(self):
        """write_event with user_id=None still inserts successfully."""
        tenant_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch("core.event_writer.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await write_event(tenant_id=tenant_id, event_type="test.event", user_id=None)

            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args
            params = call_args[0][1]
            assert params["user_id"] is None

    @pytest.mark.asyncio
    async def test_write_event_handles_none_session_id(self):
        """write_event with session_id=None still inserts successfully."""
        tenant_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch("core.event_writer.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await write_event(tenant_id=tenant_id, event_type="test.event", session_id=None)

            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args
            params = call_args[0][1]
            assert params["session_id"] is None

    @pytest.mark.asyncio
    async def test_write_event_handles_none_payload(self):
        """write_event with payload=None defaults to empty JSON object."""
        tenant_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch("core.event_writer.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await write_event(tenant_id=tenant_id, event_type="test.event", payload=None)

            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args
            params = call_args[0][1]
            assert params["payload"] == "{}"

    @pytest.mark.asyncio
    async def test_write_event_generates_unique_id(self):
        """Each write_event call generates a new UUID for the event."""
        tenant_id = uuid.uuid4()
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch("core.event_writer.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await write_event(tenant_id=tenant_id, event_type="event.a")
            await write_event(tenant_id=tenant_id, event_type="event.b")

            assert mock_db.execute.call_count == 2
            id1 = mock_db.execute.call_args_list[0][0][1]["id"]
            id2 = mock_db.execute.call_args_list[1][0][1]["id"]
            assert id1 != id2

    @pytest.mark.asyncio
    async def test_write_event_payload_is_valid_json(self):
        """Payload is serialized as JSON string with ensure_ascii=False for Chinese chars."""
        tenant_id = uuid.uuid4()
        payload = {"省份": "广东", "分数": 600}
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()

        with patch("core.event_writer.async_session") as mock_async_session:
            mock_async_session.return_value.__aenter__.return_value = mock_db

            await write_event(tenant_id=tenant_id, event_type="test.event", payload=payload)

            call_args = mock_db.execute.call_args
            params = call_args[0][1]
            parsed = json.loads(params["payload"])
            assert parsed["省份"] == "广东"
            assert parsed["分数"] == 600
