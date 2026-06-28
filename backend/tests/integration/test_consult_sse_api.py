"""咨询 SSE 路由集成测试 — 验证端到端 SSE 事件序列。

测试策略：
- 直接调用路由处理函数（绕过 HTTP 中间件，避免 DB 依赖）
- Mock LLM (ChatOpenAI), ChromaDB (search_similar), DB (async_session)
- 解析 SSE 事件序列，验证契约：
  * 非法 session_id → error 事件
  * 不存在的 session_id → SESSION_NOT_FOUND 事件
  * 合法流程：thinking → intent → admission_data → token* → validation → done
"""
import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """覆盖 conftest.py 的 setup_db — 跳过 DB 连接。"""
    yield


def _parse_sse(raw_text: str) -> list[dict]:
    """解析 SSE 响应文本为事件列表。"""
    events = []
    for block in raw_text.split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
    return events


async def _consume_streaming_response(response) -> str:
    """消费 StreamingResponse 的 body_iterator，返回完整文本。"""
    chunks = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, bytes):
            chunks.append(chunk.decode())
        else:
            chunks.append(chunk)
    return "".join(chunks)


def _make_mock_request(headers: dict | None = None) -> MagicMock:
    """创建 mock Request 对象。"""
    request = MagicMock()
    request.headers = headers or {}
    return request


@pytest.mark.asyncio
async def test_consult_rejects_non_consult_session_prefix():
    """非 sess_consult_ 前缀的 session_id → error INVALID_SESSION。"""
    from api.routes.consult import send_consult_message
    from schemas.consult import ConsultMessageRequest

    body = ConsultMessageRequest(
        session_id="sess_recommend_xxx",  # 错误前缀
        tenant_slug="scnu",
        message="我想了解计算机专业",
    )

    response = await send_consult_message(body, _make_mock_request())
    raw = await _consume_streaming_response(response)
    events = _parse_sse(raw)

    assert any(e.get("type") == "error" and e.get("code") == "INVALID_SESSION" for e in events)


@pytest.mark.asyncio
async def test_consult_returns_session_not_found_for_unknown_session():
    """sess_consult_ 前缀但 DB 中无记录 → SESSION_NOT_FOUND。"""
    from api.routes.consult import send_consult_message
    from schemas.consult import ConsultMessageRequest

    body = ConsultMessageRequest(
        session_id="sess_consult_unknown123",
        tenant_slug="scnu",
        message="想了解专业",
    )

    with patch("api.routes.consult.get_session", new=AsyncMock(return_value=None)):
        response = await send_consult_message(body, _make_mock_request())

    raw = await _consume_streaming_response(response)
    events = _parse_sse(raw)

    assert any(e.get("type") == "error" and e.get("code") == "SESSION_NOT_FOUND" for e in events)


@pytest.mark.asyncio
async def test_consult_full_sse_flow_with_mocked_llm():
    """完整 SSE 流程：thinking → intent → admission_data → token* → validation → done。

    Mock 所有外部依赖：get_session, save_message, get_chat_history, load_prompt,
    resolve_tenant, query_admission_data, validate_response, ChatOpenAI, async_session
    """
    from api.routes.consult import send_consult_message
    from schemas.consult import ConsultMessageRequest

    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    mock_session.session_id = "sess_consult_test12345"
    mock_session.tenant_slug = "scnu"
    mock_session.province = "广东"

    mock_tenant = MagicMock()
    mock_tenant.id = uuid.uuid4()
    mock_tenant.slug = "scnu"
    mock_tenant.config = {"brand": {"name": "华南师范大学"}}

    def _make_chunk(content: str):
        c = MagicMock()
        c.content = content
        return c

    intent_chunk = _make_chunk(json.dumps({
        "intent_type": "data_query",
        "majors": ["计算机科学与技术"],
        "province": "广东",
        "year": 2025,
        "need_admission_data": True,
    }))

    gen_chunks = [_make_chunk("华师计算机专业"), _make_chunk("分数约620分。")]

    class _MockLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self._gen_count = 0

        async def ainvoke(self, msgs):
            return intent_chunk

        async def astream(self, msgs):
            self._gen_count += 1
            for c in gen_chunks:
                yield c

    mock_college_result = MagicMock()
    mock_college_result.scalar_one_or_none.return_value = None  # 跳过 admission 查询

    with patch("api.routes.consult.get_session", new=AsyncMock(return_value=mock_session)), \
         patch("api.routes.consult.save_message", new=AsyncMock(return_value={"role": "assistant", "content": "华师计算机专业分数约620分。"})), \
         patch("api.routes.consult.get_chat_history", new=AsyncMock(return_value=[])), \
         patch("api.routes.consult.build_profile_summary", return_value=None), \
         patch("api.routes.consult.load_prompt", new=AsyncMock(return_value="{slots_summary}{admission_table}{knowledge_context}")), \
         patch("api.routes.consult.resolve_tenant", new=AsyncMock(return_value=mock_tenant)), \
         patch("api.routes.consult.query_admission_data", new=AsyncMock(return_value=[])), \
         patch("api.routes.consult.validate_response", return_value=[]), \
         patch("api.routes.consult.ChatOpenAI", _MockLLM), \
         patch("api.routes.consult.async_session") as mock_async_session, \
         patch("api.routes.consult.write_event", new=AsyncMock()):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_college_result)
        mock_async_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_async_session.return_value.__aexit__ = AsyncMock(return_value=None)

        body = ConsultMessageRequest(
            session_id="sess_consult_test12345",
            tenant_slug="scnu",
            message="我想了解计算机专业录取分数",
        )
        response = await send_consult_message(body, _make_mock_request())
        # 必须在 with 块内消费流（patches 须保持激活）
        raw = await _consume_streaming_response(response)

    events = _parse_sse(raw)
    event_types = [e.get("type") for e in events]

    # 验证关键事件按预期顺序出现
    assert "thinking" in event_types, f"Missing thinking. Got: {event_types}"
    assert "intent" in event_types, f"Missing intent. Got: {event_types}"
    assert "admission_data" in event_types, f"Missing admission_data. Got: {event_types}"
    assert "token" in event_types, f"Missing token. Got: {event_types}"
    assert "validation" in event_types, f"Missing validation. Got: {event_types}"
    assert "done" in event_types, f"Missing done. Got: {event_types}"

    # 验证 intent payload
    intent_event = next(e for e in events if e.get("type") == "intent")
    assert intent_event["intent"]["intent_type"] == "data_query"
    assert intent_event["intent"]["majors"] == ["计算机科学与技术"]

    # 验证 validation 通过
    validation_event = next(e for e in events if e.get("type") == "validation")
    assert validation_event["passed"] is True
    assert validation_event["regenerated"] is False

    # 验证 done 事件
    done_event = next(e for e in events if e.get("type") == "done")
    assert done_event["session_id"] == "sess_consult_test12345"
    assert done_event["validation_passed"] is True


@pytest.mark.asyncio
async def test_consult_validation_failure_triggers_regeneration():
    """后置校验失败 + admission_rows 非空 → 触发重生成流程。

    验证：validation(passed=False) → regeneration → token* → validation(passed=True)
    """
    from api.routes.consult import send_consult_message
    from schemas.consult import ConsultMessageRequest
    from services.consult_validator import ValidationIssue

    mock_session = MagicMock()
    mock_session.id = uuid.uuid4()
    mock_session.session_id = "sess_consult_test_regen"
    mock_session.tenant_slug = "scnu"
    mock_session.province = "广东"

    mock_tenant = MagicMock()
    mock_tenant.id = uuid.uuid4()
    mock_tenant.slug = "scnu"
    mock_tenant.config = {"brand": {"name": "华南师范大学"}}

    def _make_chunk(content: str):
        c = MagicMock()
        c.content = content
        return c

    intent_chunk = _make_chunk(json.dumps({
        "intent_type": "data_query",
        "majors": ["计算机科学与技术"],
        "need_admission_data": True,
        "province": "广东",
    }))

    first_gen = [_make_chunk("计算机录取位次 5000。")]
    regen_chunks = [_make_chunk("计算机录取位次 8000。")]

    class _MockLLM:
        def __init__(self, **kwargs):
            self._gen_count = 0

        async def ainvoke(self, msgs):
            return intent_chunk

        async def astream(self, msgs):
            self._gen_count += 1
            if self._gen_count == 1:
                for c in first_gen:
                    yield c
            else:
                for c in regen_chunks:
                    yield c

    admission_rows = [{
        "major_name": "计算机科学与技术",
        "min_rank": 8000,
        "min_score": 620,
        "year": 2025,
        "province": "广东",
        "batch": "本科批",
        "subject_requirements": "物理+化学",
    }]

    issue = ValidationIssue(
        major_in_reply="计算机科学与技术",
        metric="min_rank",
        value_in_reply=5000,
        matched_db_row={"min_rank": 8000},
        issue_type="mismatch",
    )

    mock_college = MagicMock()
    mock_college.id = uuid.uuid4()
    mock_college_result = MagicMock()
    mock_college_result.scalar_one_or_none.return_value = mock_college

    validate_call_count = [0]
    def _validate_side_effect(content, rows):
        validate_call_count[0] += 1
        if validate_call_count[0] == 1:
            return [issue]
        return []

    with patch("api.routes.consult.get_session", new=AsyncMock(return_value=mock_session)), \
         patch("api.routes.consult.save_message", new=AsyncMock(return_value={"role": "assistant", "content": "x"})), \
         patch("api.routes.consult.get_chat_history", new=AsyncMock(return_value=[])), \
         patch("api.routes.consult.build_profile_summary", return_value=None), \
         patch("api.routes.consult.load_prompt", new=AsyncMock(return_value="{slots_summary}{admission_table}{knowledge_context}")), \
         patch("api.routes.consult.resolve_tenant", new=AsyncMock(return_value=mock_tenant)), \
         patch("api.routes.consult.query_admission_data", new=AsyncMock(return_value=admission_rows)), \
         patch("api.routes.consult.validate_response", side_effect=_validate_side_effect), \
         patch("api.routes.consult.ChatOpenAI", _MockLLM), \
         patch("api.routes.consult.async_session") as mock_async_session, \
         patch("api.routes.consult.write_event", new=AsyncMock()):
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_college_result)
        mock_async_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_async_session.return_value.__aexit__ = AsyncMock(return_value=None)

        body = ConsultMessageRequest(
            session_id="sess_consult_test_regen",
            tenant_slug="scnu",
            message="计算机录取位次？",
        )
        response = await send_consult_message(body, _make_mock_request())
        # 必须在 with 块内消费流（patches 须保持激活）
        raw = await _consume_streaming_response(response)

    events = _parse_sse(raw)
    event_types = [e.get("type") for e in events]

    # 两个 validation 事件（第一次失败，第二次通过）
    validation_events = [e for e in events if e.get("type") == "validation"]
    assert len(validation_events) == 2, f"Expected 2 validation events, got {len(validation_events)}"

    assert validation_events[0]["passed"] is False
    assert validation_events[0]["issues_count"] >= 1
    assert validation_events[0]["regenerated"] is False

    assert validation_events[1]["passed"] is True
    assert validation_events[1]["regenerated"] is True

    # 出现 regeneration 事件
    assert "regeneration" in event_types

    # done 事件
    done_event = next(e for e in events if e.get("type") == "done")
    assert done_event["regenerated"] is True
    assert done_event["validation_passed"] is True
