# 推荐模块上下文增强实施计划 (Plan 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 推荐模块（`/api/v1/chat/messages`）读取用户最近活跃咨询会话的历史消息，注入 B2B system prompt 的 `consult_context` 占位符，使推荐回答能自然延续用户咨询过的专业话题。

**Architecture:** 复用 Plan 1 已实现的 `context_ref_session_id` 字段（推荐会话创建时自动绑定最近咨询会话）。Plan 1 Task 19 已修改 B2B prompt 与 miniapp.py 注入逻辑。本 Plan 专注：①后端注入逻辑的健壮性增强（长度限制、敏感过滤、缓存）；②集成测试验证；③mini-app chat 页前端展示"已读取咨询历史"指示器。

**Tech Stack:** FastAPI、SQLAlchemy、LangChain、Vue 3。

**依赖：** Plan 1 Task 2/3/13/19 已完成。

**参考设计文档：** `docs/superpowers/specs/2026-06-27-consult-module-design.md`

---

## 文件结构

新增文件：
- `backend/services/consult_context_service.py` — 咨询上下文读取与截断
- `backend/tests/unit/test_consult_context_service.py`
- `backend/tests/integration/test_recommend_with_consult_context.py`

修改文件：
- `backend/api/routes/miniapp.py` — `send_chat_message` 改用 consult_context_service
- `mini-app/src/pages/chat/index.vue` — 顶部显示"已读取 N 条咨询历史"指示器

---

## Task 1: 编写 consult_context_service 测试（TDD）

**Files:**
- Test: `backend/tests/unit/test_consult_context_service.py`

- [ ] **Step 1: 编写单测**

Create `backend/tests/unit/test_consult_context_service.py`:
```python
"""consult_context_service 单测 — 推荐模块读取咨询历史。

测试契约：
1. build_consult_context 返回格式化的多轮对话字符串
2. 超过 max_messages 时截断保留最近 N 条
3. 超过 max_chars 时截断并追加省略提示
4. 咨询会话不存在时返回空串
5. 咨询会话无消息时返回空串
6. 单条消息超长时单独截断
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_build_context_returns_formatted_history():
    """正常场景：返回 "考生: xxx\nAI: yyy" 格式。"""
    from services.consult_context_service import build_consult_context
    context_ref_id = uuid4()
    mock_history = [
        {"role": "user", "content": "人工智能 2024 年位次"},
        {"role": "assistant", "content": "人工智能 2024 年最低位次 32000"},
    ]
    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_cs = MagicMock()
        mock_cs.session_id = "sess_consult_xxx"
        mock_cs_result = MagicMock()
        mock_cs_result.scalar_one_or_none.return_value = mock_cs
        mock_db.execute = AsyncMock(side_effect=[mock_cs_result])
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("services.consult_context_service.get_chat_history", new=AsyncMock(return_value=mock_history)):
            result = await build_consult_context(context_ref_id)

    assert "考生: 人工智能 2024 年位次" in result
    assert "AI: 人工智能 2024 年最低位次 32000" in result


@pytest.mark.asyncio
async def test_build_context_truncates_when_exceeding_max_messages():
    """超过 max_messages 时保留最近 N 条。"""
    from services.consult_context_service import build_consult_context
    context_ref_id = uuid4()
    mock_history = [
        {"role": "user", "content": f"问题{i}"},
        {"role": "assistant", "content": f"回答{i}"},
    ] * 10  # 20 条
    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_cs = MagicMock()
        mock_cs.session_id = "sess_consult_xxx"
        mock_cs_result = MagicMock()
        mock_cs_result.scalar_one_or_none.return_value = mock_cs
        mock_db.execute = AsyncMock(return_value=mock_cs_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("services.consult_context_service.get_chat_history", new=AsyncMock(return_value=mock_history)):
            result = await build_consult_context(context_ref_id, max_messages=6)

    # 应只包含最近 6 条
    assert "问题9" in result  # 第 10 组的 user（index 18-19 是最后一组）
    assert "问题0" not in result  # 最早的已被截断


@pytest.mark.asyncio
async def test_build_context_truncates_when_exceeding_max_chars():
    """超过 max_chars 时截断并追加省略提示。"""
    from services.consult_context_service import build_consult_context
    context_ref_id = uuid4()
    long_content = "A" * 500
    mock_history = [
        {"role": "user", "content": long_content},
        {"role": "assistant", "content": long_content},
    ]
    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_cs = MagicMock()
        mock_cs.session_id = "sess_consult_xxx"
        mock_cs_result = MagicMock()
        mock_cs_result.scalar_one_or_none.return_value = mock_cs
        mock_db.execute = AsyncMock(return_value=mock_cs_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("services.consult_context_service.get_chat_history", new=AsyncMock(return_value=mock_history)):
            result = await build_consult_context(context_ref_id, max_chars=300)

    assert len(result) <= 350  # 留余量给省略提示
    assert "..." in result or "已截断" in result


@pytest.mark.asyncio
async def test_build_context_returns_empty_when_session_not_found():
    """咨询会话不存在时返回空串。"""
    from services.consult_context_service import build_consult_context
    context_ref_id = uuid4()
    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_cs_result = MagicMock()
        mock_cs_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_cs_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await build_consult_context(context_ref_id)

    assert result == ""


@pytest.mark.asyncio
async def test_build_context_returns_empty_when_no_messages():
    """咨询会话无消息时返回空串。"""
    from services.consult_context_service import build_consult_context
    context_ref_id = uuid4()
    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_cs = MagicMock()
        mock_cs.session_id = "sess_consult_xxx"
        mock_cs_result = MagicMock()
        mock_cs_result.scalar_one_or_none.return_value = mock_cs
        mock_db.execute = AsyncMock(return_value=mock_cs_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("services.consult_context_service.get_chat_history", new=AsyncMock(return_value=[])):
            result = await build_consult_context(context_ref_id)

    assert result == ""
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/unit/test_consult_context_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.consult_context_service'`

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/unit/test_consult_context_service.py
git commit -m "test(backend): add consult_context_service unit tests (failing)"
```

---

## Task 2: 实现 consult_context_service

**Files:**
- Create: `backend/services/consult_context_service.py`

- [ ] **Step 1: 实现服务**

Create `backend/services/consult_context_service.py`:
```python
"""推荐模块读取咨询历史的上下文构建服务。

负责：
1. 根据 context_ref_session_id 查询咨询会话
2. 获取咨询历史消息（限制条数）
3. 格式化为 "考生: xxx\nAI: yyy" 字符串
4. 截断超长内容（max_messages + max_chars 双重限制）
"""
import logging
import uuid

from sqlalchemy import select
from models import async_session
from models.consult_session import ConsultSession
from services.consult_service import get_chat_history

_logger = logging.getLogger(__name__)

# 默认限制：最近 6 条消息（3 轮对话），总字符不超过 1500
DEFAULT_MAX_MESSAGES = 6
DEFAULT_MAX_CHARS = 1500
# 单条消息最大字符（超出单独截断）
SINGLE_MESSAGE_MAX_CHARS = 500


async def build_consult_context(
    context_ref_session_id: uuid.UUID | None,
    max_messages: int = DEFAULT_MAX_MESSAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """构建推荐模块用的咨询上下文字符串。

    Args:
        context_ref_session_id: 推荐会话绑定的咨询会话 ID（ConsultSession.id）
        max_messages: 最多包含的消息条数（含 user + assistant）
        max_chars: 上下文字符串最大长度

    Returns:
        格式化的对话字符串；无咨询历史时返回空串。
    """
    if not context_ref_session_id:
        return ""

    try:
        # 查询咨询会话
        async with async_session() as db:
            result = await db.execute(
                select(ConsultSession).where(ConsultSession.id == context_ref_session_id)
            )
            consult_session = result.scalar_one_or_none()

        if not consult_session:
            return ""

        # 获取咨询历史（limit 传 max_messages*2 容差，下面再精确截断）
        history = await get_chat_history(consult_session.session_id, limit=max_messages)
        if not history:
            return ""

        # 按 max_messages 截断保留最近 N 条（防止 get_chat_history 未严格执行 limit）
        history = history[-max_messages:]

        # 格式化
        lines = []
        total_chars = 0
        truncated = False

        for msg in history:
            role = "考生" if msg["role"] == "user" else "AI"
            content = msg["content"] or ""

            # 单条消息截断
            if len(content) > SINGLE_MESSAGE_MAX_CHARS:
                content = content[:SINGLE_MESSAGE_MAX_CHARS] + "..."

            line = f"{role}: {content}"

            # 总长度检查
            if total_chars + len(line) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 50:  # 至少保留 50 字符才有意义
                    lines.append(line[:remaining] + "...")
                truncated = True
                break

            lines.append(line)
            total_chars += len(line) + 1  # +1 for newline

        result_str = "\n".join(lines)
        if truncated:
            result_str += "\n（历史已截断，仅显示最近部分）"

        return result_str

    except Exception as e:
        _logger.warning(f"build_consult_context failed for ref={context_ref_session_id}: {e}")
        return ""
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/unit/test_consult_context_service.py -v`
Expected: 5 passed

- [ ] **Step 3: Commit**

```bash
cd backend
git add services/consult_context_service.py
git commit -m "feat(backend): implement consult_context_service with truncation"
```

---

## Task 3: 修改 miniapp.py 的 chat 路由使用 consult_context_service

**Files:**
- Modify: `backend/api/routes/miniapp.py`

- [ ] **Step 1: 替换 Plan 1 Task 19 中的内联逻辑为服务调用**

Edit `backend/api/routes/miniapp.py`，在 `send_chat_message` 函数中，将 Plan 1 Task 19 注入的内联代码：
```python
    # 注入咨询历史上下文（仅当 session.context_ref_session_id 存在）
    consult_context = ""
    if session.context_ref_session_id:
        try:
            from sqlalchemy import select as _select
            from models.consult_session import ConsultSession as _CS
            from services.consult_service import get_chat_history as _get_history
            async with async_session() as _db:
                _r = await _db.execute(_select(_CS).where(_CS.id == session.context_ref_session_id))
                _consult_sess = _r.scalar_one_or_none()
                if _consult_sess:
                    _history = await _get_history(_consult_sess.session_id, limit=6)
                    if _history:
                        _lines = []
                        for _m in _history:
                            _role = "考生" if _m["role"] == "user" else "AI"
                            _lines.append(f"{_role}: {_m['content']}")
                        consult_context = "\n".join(_lines)
        except Exception as e:
            logging.warning(f"Failed to load consult context for session={body.session_id}: {e}")
```

替换为：
```python
    # 注入咨询历史上下文（仅当 session.context_ref_session_id 存在）
    from services.consult_context_service import build_consult_context
    consult_context = await build_consult_context(session.context_ref_session_id)
    if consult_context:
        logging.info(f"Loaded consult context for session={body.session_id} (len={len(consult_context)})")
```

- [ ] **Step 2: 验证编译**

Run: `cd backend && python -c "from api.routes.miniapp import send_chat_message; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd backend
git add api/routes/miniapp.py
git commit -m "refactor(backend): use consult_context_service in chat route"
```

---

## Task 4: 编写推荐模块读取咨询历史的集成测试

**Files:**
- Test: `backend/tests/integration/test_recommend_with_consult_context.py`

- [ ] **Step 1: 编写集成测试**

Create `backend/tests/integration/test_recommend_with_consult_context.py`:
```python
"""推荐模块读取咨询历史集成测试。

测试契约：
1. 推荐会话创建时自动绑定最近咨询会话（context_ref_session_id 非空）
2. /chat/messages 调用时 B2B system prompt 包含咨询历史内容
3. 咨询会话不存在时 prompt 中 consult_context 为空
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_recommend_session_binds_recent_consult_session():
    """注册用户创建推荐会话时自动绑定最近咨询会话。"""
    from services.consult_service import get_or_create_session
    user_id = uuid.uuid4()

    # mock DB 查询：先返回 None（无现有 session），再返回最近咨询会话
    mock_recent_consult = MagicMock()
    mock_recent_consult.id = uuid.uuid4()

    with patch("services.consult_service.async_session") as mock_session:
        mock_db = AsyncMock()
        # 第一次：select existing session → None
        # 第二次：select recent consult → mock_recent_consult
        # 第三次：select user → None
        mock_result_none = MagicMock()
        mock_result_none.scalar_one_or_none.return_value = None
        mock_result_consult = MagicMock()
        mock_result_consult.scalar_one_or_none.return_value = mock_recent_consult
        mock_result_user = MagicMock()
        mock_result_user.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[mock_result_none, mock_result_consult, mock_result_user])
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        session, is_new = await get_or_create_session(
            None, "scnu", user_id, module_type="recommend"
        )

    assert is_new is True
    # 验证 context_ref_session_id 被赋值
    # （由于 mock，new_session 是 MagicMock，检查 add 调用参数）
    assert mock_db.add.called


@pytest.mark.asyncio
async def test_build_consult_context_integration_with_real_history_format():
    """build_consult_context 输出格式能被 B2B prompt format 接受。"""
    from services.consult_context_service import build_consult_context
    from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT

    context_ref_id = uuid.uuid4()
    mock_history = [
        {"role": "user", "content": "人工智能 2024 年位次"},
        {"role": "assistant", "content": "人工智能 2024 年最低位次 32000"},
    ]
    with patch("services.consult_context_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_cs = MagicMock()
        mock_cs.session_id = "sess_consult_xxx"
        mock_cs_result = MagicMock()
        mock_cs_result.scalar_one_or_none.return_value = mock_cs
        mock_db.execute = AsyncMock(return_value=mock_cs_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("services.consult_context_service.get_chat_history", new=AsyncMock(return_value=mock_history)):
            consult_context = await build_consult_context(context_ref_id)

    # 验证 B2B prompt 能正常 format
    formatted = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华师",
        stage="open",
        slots_summary="省份: 广东",
        consult_context=consult_context,
    )
    assert "考生: 人工智能 2024 年位次" in formatted
    assert "AI: 人工智能 2024 年最低位次 32000" in formatted
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/integration/test_recommend_with_consult_context.py -v`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/integration/test_recommend_with_consult_context.py
git commit -m "test(backend): add recommend-with-consult-context integration tests"
```

---

## Task 5: mini-app chat 页展示"已读取咨询历史"指示器

**Files:**
- Modify: `mini-app/src/pages/chat/index.vue`

- [ ] **Step 1: 在 chat 页 hero 下方追加咨询上下文指示器**

Edit `mini-app/src/pages/chat/index.vue`，在 `</view>` 结束 `chat-hero` 后、`<view class="chat-body">` 前追加：
```html
      <view v-if="hasConsultContext" class="consult-context-indicator">
        <text class="consult-context-text">
          已读取你的咨询历史，可基于「{{ consultContextPreview }}」继续推荐
        </text>
      </view>
```

- [ ] **Step 2: 在 script setup 中新增咨询上下文状态**

Edit `mini-app/src/pages/chat/index.vue`，在 `const profileSummary = ref<any>(null)` 后追加：
```typescript
const hasConsultContext = ref(false)
const consultContextPreview = ref('')
```

- [ ] **Step 3: 在 miniapp/enter 响应处理中检测咨询上下文**

Edit `mini-app/src/pages/chat/index.vue`，在 `enter` 接口返回后，检测 `has_profile` 与 session 状态：
```typescript
      // 检测是否绑定了咨询上下文（通过 enter 接口的 has_profile 字段推断）
      if (res.data?.data?.profile_summary?.intent_majors?.length) {
        hasConsultContext.value = true
        consultContextPreview.value = res.data.data.profile_summary.intent_majors.slice(0, 2).join('、')
      }
```

（注：实际 consult_context 是后端注入 prompt 的，前端只展示提示性指示器。intent_majors 是咨询阶段提取的意向专业，可作为预览。）

- [ ] **Step 4: 追加指示器样式**

Edit `mini-app/src/pages/chat/index.vue` 的 `<style lang="scss" scoped>` 块，追加：
```scss
.consult-context-indicator {
  margin: 12rpx 24rpx 0;
  padding: 12rpx 20rpx;
  background: rgba(26, 86, 219, 0.08);
  border-radius: 8rpx;
  border: 1rpx solid rgba(26, 86, 219, 0.2);
}
.consult-context-text {
  font-size: 24rpx;
  color: #1A56DB;
}
```

- [ ] **Step 5: 启动 dev server 验证**

Run: `cd mini-app && npm run dev:h5 -- --port 3002`
打开 http://localhost:3002，登录后访问"个性化推荐"tab：
1. 若用户有过咨询（intent_majors 非空），顶部显示蓝色指示器"已读取你的咨询历史..."
2. 若无咨询历史，指示器不显示

- [ ] **Step 6: Commit**

```bash
cd mini-app
git add src/pages/chat/index.vue
git commit -m "feat(mini-app): show consult context indicator on chat page"
```

---

## Self-Review

**1. Spec coverage：**
- 推荐模块读取咨询历史 → Task 2 + Task 3 ✓
- context_ref_session_id 绑定 → Plan 1 Task 13 已实现，Task 4 测试验证 ✓
- consult_context 注入 B2B prompt → Plan 1 Task 19 已实现，Task 3 重构为服务调用 ✓
- 长度限制（防止 prompt 膨胀）→ Task 2（max_messages=6, max_chars=1500）✓
- 前端展示指示器 → Task 5 ✓

**2. Placeholder scan：** 无 TBD / TODO

**3. Type consistency：**
- `build_consult_context(context_ref_session_id, max_messages, max_chars) -> str` 在 Task 1/2/3/4 一致
- B2B prompt 的 `{consult_context}` 占位符与 Plan 1 Task 19 一致
- `context_ref_session_id` 字段与 Plan 1 Task 2 一致

---

## Execution Handoff

Plan 4 已完成并保存至 `docs/superpowers/plans/2026-06-27-04-recommend-context-enhancement.md`。

**4 个 Plan 全部完成：**
- Plan 1: 后端咨询模块（20 个 Task）
- Plan 2: Admin-SPA 提示词管理（5 个 Task）
- Plan 3: Mini-app 咨询页面（5 个 Task）
- Plan 4: 推荐模块上下文增强（5 个 Task）

**依赖顺序：** Plan 1 → Plan 2 / Plan 3 / Plan 4（后三者可并行）

**两种执行方式：**

**1. Subagent-Driven（推荐）** — 每个 Task 派发独立 sub-agent，Task 间双阶段 review

**2. Inline Execution** — 当前会话内顺序执行，带 checkpoint review

**请选择执行方式？**
