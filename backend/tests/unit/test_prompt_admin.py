"""prompt_admin 路由单测 — 提示词模板 CRUD + 同步。

测试契约：
1. GET /admin/prompts — 列出租户所有 prompt_key 及当前 active 版本
2. GET /admin/prompts/{prompt_key} — 返回 active 版本内容 + 代码默认值
3. PUT /admin/prompts/{prompt_key} — 创建新版本并激活，旧版本置 is_active=False
4. PUT 无效 prompt_key → 400
5. POST /admin/prompts/sync — 触发代码常量同步
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from agents.conversation.prompts_consult import CODE_DEFAULTS, PROMPT_FILE_MAP


# 纯单元测试（mock async_session + 依赖）— 覆盖 conftest.py 的 autouse setup_db
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _make_template_row(prompt_key="consult_system", version=1, content="default", is_active=True):
    row = MagicMock()
    row.id = uuid.uuid4()
    row.tenant_slug = "scnu"
    row.prompt_key = prompt_key
    row.content = content
    row.version = version
    row.is_active = is_active
    row.updated_at = MagicMock(isoformat=MagicMock(return_value="2026-06-27T00:00:00"))
    return row


@pytest.mark.asyncio
async def test_list_prompts_returns_all_keys_with_active_version():
    """GET /admin/prompts — 返回所有已知 prompt_key 及 active 版本信息。"""
    from api.routes.prompt_admin import list_prompts

    active_row = _make_template_row(prompt_key="consult_system", version=2, content="v2", is_active=True)

    with patch("api.routes.prompt_admin.async_session") as mock_session, \
         patch("api.routes.prompt_admin.CODE_DEFAULTS", CODE_DEFAULTS):
        mock_db = AsyncMock()
        # 查询返回 active 记录
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [active_row]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock tenant + user deps
        tenant = MagicMock(slug="scnu")
        user = MagicMock(user_id=uuid.uuid4())

        result = await list_prompts(tenant=tenant, _user=user)

        assert "prompts" in result
        keys = {p["prompt_key"] for p in result["prompts"]}
        # All CODE_DEFAULTS keys should appear
        assert set(CODE_DEFAULTS.keys()).issubset(keys)
        # consult_system has active version 2
        consult_entry = next(p for p in result["prompts"] if p["prompt_key"] == "consult_system")
        assert consult_entry["active_version"] == 2
        assert consult_entry["has_db_record"] is True


@pytest.mark.asyncio
async def test_list_prompts_shows_no_db_record_for_missing_keys():
    """DB 中无记录的 prompt_key 仍应列出，has_db_record=False。"""
    from api.routes.prompt_admin import list_prompts

    with patch("api.routes.prompt_admin.async_session") as mock_session, \
         patch("api.routes.prompt_admin.CODE_DEFAULTS", CODE_DEFAULTS):
        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []  # No DB records
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        tenant = MagicMock(slug="scnu")
        user = MagicMock(user_id=uuid.uuid4())

        result = await list_prompts(tenant=tenant, _user=user)

        for p in result["prompts"]:
            assert p["has_db_record"] is False
            assert p["active_version"] is None


@pytest.mark.asyncio
async def test_get_prompt_detail_returns_active_content_and_default():
    """GET /admin/prompts/{prompt_key} — 返回 active 内容 + 代码默认值。"""
    from api.routes.prompt_admin import get_prompt_detail

    active_row = _make_template_row(prompt_key="consult_system", version=3, content="custom content", is_active=True)

    with patch("api.routes.prompt_admin.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = active_row
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        tenant = MagicMock(slug="scnu")
        user = MagicMock(user_id=uuid.uuid4())

        result = await get_prompt_detail("consult_system", tenant=tenant, _user=user)

        assert result["prompt_key"] == "consult_system"
        assert result["active_version"] == 3
        assert result["content"] == "custom content"
        assert result["code_default"] == CODE_DEFAULTS["consult_system"]
        assert result["is_modified"] is True  # content != code_default


@pytest.mark.asyncio
async def test_get_prompt_detail_returns_default_when_no_db_record():
    """DB 无记录时返回 code_default，active_version=None。"""
    from api.routes.prompt_admin import get_prompt_detail

    with patch("api.routes.prompt_admin.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        tenant = MagicMock(slug="scnu")
        user = MagicMock(user_id=uuid.uuid4())

        result = await get_prompt_detail("consult_system", tenant=tenant, _user=user)

        assert result["active_version"] is None
        assert result["content"] == CODE_DEFAULTS["consult_system"]
        assert result["code_default"] == CODE_DEFAULTS["consult_system"]
        assert result["is_modified"] is False


@pytest.mark.asyncio
async def test_get_prompt_detail_invalid_key_returns_400():
    """无效 prompt_key → HTTPException 400。"""
    from api.routes.prompt_admin import get_prompt_detail
    from fastapi import HTTPException

    tenant = MagicMock(slug="scnu")
    user = MagicMock(user_id=uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await get_prompt_detail("invalid_key_xyz", tenant=tenant, _user=user)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_prompt_creates_new_version_and_deactivates_old():
    """PUT /admin/prompts/{prompt_key} — 创建新版本并激活，旧版本 is_active=False。"""
    from api.routes.prompt_admin import update_prompt

    old_row = _make_template_row(prompt_key="consult_system", version=1, content="old", is_active=True)

    with patch("api.routes.prompt_admin.async_session") as mock_session, \
         patch("api.routes.prompt_admin.sync_to_code_with_retry", new=AsyncMock(return_value=MagicMock(success=True, attempts=1, error=None))):
        mock_db = AsyncMock()
        # 1st call: get max version → returns 1
        # 2nd call: deactivate old → execute
        # 3rd call: refresh new row
        max_result = MagicMock()
        max_result.scalar_one_or_none.return_value = 1
        mock_db.execute = AsyncMock(return_value=max_result)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        tenant = MagicMock(slug="scnu")
        user = MagicMock(user_id=uuid.uuid4())

        body = MagicMock(content="new content")
        result = await update_prompt("consult_system", body=body, tenant=tenant, _user=user)

        assert result["version"] == 2
        assert result["is_active"] is True
        # Verify add was called (new template created)
        assert mock_db.add.called
        # Verify commit was called
        assert mock_db.commit.called


@pytest.mark.asyncio
async def test_update_prompt_invalid_key_returns_400():
    """PUT 无效 prompt_key → 400。"""
    from api.routes.prompt_admin import update_prompt
    from fastapi import HTTPException

    tenant = MagicMock(slug="scnu")
    user = MagicMock(user_id=uuid.uuid4())
    body = MagicMock(content="x")

    with pytest.raises(HTTPException) as exc_info:
        await update_prompt("invalid_key", body=body, tenant=tenant, _user=user)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_sync_prompts_triggers_sync_for_all_keys():
    """POST /admin/prompts/sync — 对所有 prompt_key 触发代码同步。"""
    from api.routes.prompt_admin import sync_prompts

    with patch("api.routes.prompt_admin.sync_to_code_with_retry", new=AsyncMock(return_value=MagicMock(success=True, attempts=1, error=None))) as mock_sync, \
         patch("api.routes.prompt_admin.load_prompt", new=AsyncMock(return_value="db content")):
        tenant = MagicMock(slug="scnu")
        user = MagicMock(user_id=uuid.uuid4())

        result = await sync_prompts(tenant=tenant, _user=user)

        assert "results" in result
        assert len(result["results"]) == len(CODE_DEFAULTS)
        assert all(r["success"] for r in result["results"])
        # sync_to_code_with_retry called once per key
        assert mock_sync.call_count == len(CODE_DEFAULTS)
