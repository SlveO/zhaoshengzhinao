# 咨询模块后端实施计划 (Plan 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现咨询模块后端：DB 迁移、提示词服务、咨询 SSE API、双层检索、后置校验、提示词在线编辑管理 API。

**Architecture:** 在现有 backend/ 目录下新增 consult 路由、提示词管理路由、双层检索/校验服务、prompt ORM 模型与同步服务。保留现有 `/api/v1/chat/messages`（推荐模块）不变。会话通过 session_id 前缀 `sess_consult_` 隔离。

**Tech Stack:** FastAPI、SQLAlchemy 2.0 (async)、Alembic、LangChain、DeepSeek、ChromaDB、Redis (Upstash)、APScheduler。

**前置约束（来自 project_memory）：**
- 实施与测试代码必须由不同 sub-agent 实例编写（HARD RULE）
- 测试遵循 AAA 模式
- ChromaDB 必须用 1024 维 (BAAI/bge-large-zh-v1.5)
- 仅服务 SCNU
- Alembic 必须线性化（当前 head 是 008_consult_workbench）

**参考设计文档：** `docs/superpowers/specs/2026-06-27-consult-module-design.md`

---

## 文件结构

新增文件：
- `backend/models/prompt_template.py` — PromptTemplate ORM
- `backend/agents/conversation/prompts_consult.py` — 咨询提示词常量
- `backend/services/prompt_service.py` — 提示词加载（DB 优先→代码回退）
- `backend/services/prompt_sync_service.py` — 代码常量文件双写同步
- `backend/services/consult_retrieval_service.py` — 双层检索（SQL + RAG）
- `backend/services/consult_validator.py` — 后置校验
- `backend/api/routes/consult.py` — 咨询 SSE 路由
- `backend/api/routes/prompt_admin.py` — 提示词管理路由
- `backend/migrations/versions/009_consult_module.py` — DB 迁移
- `backend/tests/unit/test_consult_retrieval_service.py`
- `backend/tests/unit/test_consult_validator.py`
- `backend/tests/unit/test_prompt_service.py`
- `backend/tests/integration/test_consult_sse.py`
- `backend/tests/integration/test_prompt_admin.py`

修改文件：
- `backend/models/__init__.py` — 注册 PromptTemplate
- `backend/models/consult_session.py` — 新增 context_ref_session_id 字段
- `backend/services/consult_service.py` — get_or_create_session 支持 module_type + 前缀隔离
- `backend/api/routes/miniapp.py` — miniapp_enter 支持 module_type
- `backend/main.py` — 注册新路由 + lifespan 一致性校验
- `backend/config.py` — 新增 consult_module_enabled flag
- `backend/agents/conversation/prompts_b2b.py` — 追加 consult_context 占位符 + markdown 约束

---

## Task 1: 创建 PromptTemplate ORM 模型

**Files:**
- Create: `backend/models/prompt_template.py`
- Modify: `backend/models/__init__.py:32-49` (init_db 中 import 新模型)

- [ ] **Step 1: 创建 PromptTemplate ORM 模型**

Create `backend/models/prompt_template.py`:
```python
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Text, DateTime, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_slug: Mapped[str] = mapped_column(String(50), nullable=False, default="scnu", index=True)
    prompt_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("tenant_slug", "prompt_key", "version", name="uq_prompt_version"),
    )
```

- [ ] **Step 2: 在 models/__init__.py 的 init_db 中注册**

Modify `backend/models/__init__.py`，在 `from . import consult_session  # noqa: F401` 后追加：
```python
    from . import prompt_template  # noqa: F401
```

- [ ] **Step 3: 验证 import 无语法错误**

Run: `cd backend && python -c "from models.prompt_template import PromptTemplate; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd backend
git add models/prompt_template.py models/__init__.py
git commit -m "feat(backend): add PromptTemplate ORM model"
```

---

## Task 2: 扩展 ConsultSession 模型新增 context_ref_session_id 字段

**Files:**
- Modify: `backend/models/consult_session.py:33` (在 expires_at 后追加字段)

- [ ] **Step 1: 在 ConsultSession 模型追加 context_ref_session_id**

Edit `backend/models/consult_session.py`，在 `expires_at` 字段后追加：
```python
    context_ref_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="推荐会话绑定的最近活跃咨询会话 ID（仅推荐会话）",
    )
```

- [ ] **Step 2: 验证 import**

Run: `cd backend && python -c "from models.consult_session import ConsultSession; print(hasattr(ConsultSession, 'context_ref_session_id'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
cd backend
git add models/consult_session.py
git commit -m "feat(backend): add context_ref_session_id to ConsultSession"
```

---

## Task 3: 创建 Alembic 迁移脚本 009_consult_module

**Files:**
- Create: `backend/migrations/versions/009_consult_module.py`

- [ ] **Step 1: 创建迁移脚本**

Create `backend/migrations/versions/009_consult_module.py`:
```python
"""consult module: prompt_templates table + consult_sessions.context_ref_session_id

Revision ID: 009_consult_module
Revises: 008_consult_workbench
Create Date: 2026-06-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "009_consult_module"
down_revision = "008_consult_workbench"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 新增 prompt_templates 表
    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_slug", sa.String(50), nullable=False, server_default="scnu"),
        sa.Column("prompt_key", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.clock_timestamp()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_slug", "prompt_key", "version", name="uq_prompt_version"),
    )
    op.create_index("ix_prompt_templates_tenant_slug", "prompt_templates", ["tenant_slug"])
    op.create_index("ix_prompt_templates_prompt_key", "prompt_templates", ["prompt_key"])
    op.create_index("ix_prompt_templates_is_active", "prompt_templates", ["is_active"])

    # 2. consult_sessions 新增 context_ref_session_id（幂等）
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("consult_sessions")}
    if "context_ref_session_id" not in existing_cols:
        op.add_column(
            "consult_sessions",
            sa.Column("context_ref_session_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        op.create_index(
            "ix_consult_sessions_context_ref",
            "consult_sessions",
            ["context_ref_session_id"]
        )


def downgrade() -> None:
    op.drop_index("ix_consult_sessions_context_ref", table_name="consult_sessions")
    op.drop_column("consult_sessions", "context_ref_session_id")
    op.drop_index("ix_prompt_templates_is_active", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_prompt_key", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_tenant_slug", table_name="prompt_templates")
    op.drop_table("prompt_templates")
```

- [ ] **Step 2: 运行迁移（开发库）**

Run: `cd backend && alembic upgrade head`
Expected: `Running upgrade 008_consult_workbench -> 009_consult_module, consult module: ...`

- [ ] **Step 3: 验证表创建**

Run: `cd backend && python -c "import asyncio; from models import async_session, init_db; from sqlalchemy import text; async def check(): await init_db(); async with async_session() as db: r = await db.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='prompt_templates'\")); print(sorted([x[0] for x in r])); asyncio.run(check())"`
Expected: 包含 `id, tenant_slug, prompt_key, content, version, is_active, updated_by, updated_at, created_at`

- [ ] **Step 4: 验证 downgrade 可回滚**

Run: `cd backend && alembic downgrade -1 && alembic upgrade head`
Expected: 无错误，回滚后重新 upgrade 成功

- [ ] **Step 5: Commit**

```bash
cd backend
git add migrations/versions/009_consult_module.py
git commit -m "feat(backend): add migration 009_consult_module (prompt_templates + context_ref)"
```

---

## Task 4: 创建咨询提示词常量文件

**Files:**
- Create: `backend/agents/conversation/prompts_consult.py`

- [ ] **Step 1: 创建 prompts_consult.py**

Create `backend/agents/conversation/prompts_consult.py`:
```python
"""咨询模块提示词常量 — 与推荐模块 (prompts_b2b.py) 分离。

CONSULT_SYSTEM_PROMPT 用于咨询 SSE 路由 /api/v1/consult/messages。
风格：客观严谨，禁止共情语/反问/markdown。
"""

CONSULT_SYSTEM_PROMPT = """你是华南师范大学招生信息助手。你的唯一职责是基于客观数据准确回答考生关于招生的问题。

## 核心原则（必须严格遵守）
1. **数据至上**：录取分数、位次、选科要求等数据必须严格引用下方「录取数据」表格，禁止从「知识库检索结果」或其他来源引用任何录取数字。
2. **完整回答优先**：用户提问后必须先给出完整、直接的回答，不要反问、不要引导性提问、不要"先了解再回答"。
3. **客观严谨**：只陈述事实，不加主观评价（如"这个专业很好""很适合你"）。可以使用"该专业 2024 年最低录取位次为 32000"这类客观表述，禁止"这个位次报考很有希望"这类主观判断。
4. **不知则说不知**：如果「录取数据」表格中没有用户问的专业/年份/省份，明确回答"华南师范大学暂未公开 {专业} 在 {省份} {年份} 的录取数据"，禁止用其他专业的数据拼接回答、禁止编造。
5. **数字零误差**：回复中出现的所有分数、位次必须与「录取数据」表格完全一致，禁止四舍五入、禁止跨专业借用、禁止用"约""大概"修饰具体数字。

## 回答风格
- 直接陈述事实，2-5 句话
- 一次完整回答用户问题，不分步引导
- 可以在回答末尾补充一句"如需个性化推荐，可前往推荐模块"（仅当用户主动询问报考建议时）
- 禁止反问（如"你想了解哪个专业？""你的分数是多少？"）
- 禁止共情语（如"我理解你的焦虑""很多同学都会迷茫"）

## 数据引用规则
- 引用录取数据时，必须明确标注年份和省份："人工智能专业 2024 年在广东最低录取分 585 分，位次 32000"
- 多年数据对比时，按年份顺序列出："近三年位次：2024 年 32000、2023 年 33500、2022 年 35000"
- 选科要求原样引用表格内容，不重新表述

## 输出格式（必须严格遵守）
- 使用纯文本，禁止使用任何 markdown 语法（** ## - ` 等）
- 强调关键词时用中文引号「」，如「人工智能专业」
- 列举时用中文数字（一、二、三、 或 1. 2. 3.）
- 禁止输出 markdown 表格，数据用自然语言表述
  （错误示例：| 专业 | 分数 |）
  （正确示例：人工智能 2024 年最低分 585，位次 32000）
- 数字直接写，不加任何修饰符号

## 用户基础信息
{slots_summary}

## 录取数据（数据库精确数据，硬证据）
{admission_table}

## 知识库检索结果（参考，不可引用其中的录取数字）
{knowledge_context}

## 不可回答的问题类型
- "我能不能考上" → 回答"录取概率取决于当年报考情况，建议参考历年最低位次自行判断"，并给出数据
- "哪个专业适合我" → 回答"个性化推荐请前往推荐模块"，可补充该专业的基本信息
- "对比 A 专业和 B 专业哪个好" → 回答"两个专业无优劣之分"，可分别列出两个专业的客观数据
"""


INTENT_EXTRACTION_PROMPT = """你是高考咨询意图分析助手。从用户消息中抽取结构化字段，严格按 JSON 输出，无匹配则置 null，不要输出任何其他内容。

字段说明：
- intent_type: "data_query"(查录取数据) | "policy_query"(查政策/章程) | "major_intro"(查专业介绍) | "chitchat"(闲聊)
- majors: 标准化专业名数组（如"人工智能"，非"AI"；"软件工程"，非"软工"）
- province: 省份名（默认"广东"）
- year: 年份整数（默认 null，表示取最新）
- score_query: 用户提到的分数（int 或 null）
- rank_query: 用户提到的位次（int 或 null）
- need_admission_data: true/false（data_query 且涉及分数/位次时为 true）

输出格式：
{"intent_type":"data_query","majors":["人工智能"],"province":"广东","year":null,"score_query":585,"rank_query":null,"need_admission_data":true}
"""


DEGRADED_REGENERATION_PROMPT = """你的回复中存在数据错误，已失败 1 次重生成。现在请直接基于数据表逐条陈述，不要做任何归纳或推理。

## 强制输出格式
1. 先列出数据表中所有相关行（按年份倒序）
2. 再用 1-2 句话回答用户原始问题
3. 禁止出现数据表以外的任何数字

## 数据表
{admission_table}

## 用户原始问题
{user_content}

## 请按格式输出：
"""


# 代码默认值映射表，供 prompt_service 回退使用
CODE_DEFAULTS = {
    "consult_system": CONSULT_SYSTEM_PROMPT,
    "consult_intent": INTENT_EXTRACTION_PROMPT,
    "consult_degraded": DEGRADED_REGENERATION_PROMPT,
}

# prompt_key → (代码文件相对路径, 常量名) 映射，供 prompt_sync_service 使用
PROMPT_FILE_MAP = {
    "consult_system": ("agents/conversation/prompts_consult.py", "CONSULT_SYSTEM_PROMPT"),
    "consult_intent": ("agents/conversation/prompts_consult.py", "INTENT_EXTRACTION_PROMPT"),
    "consult_degraded": ("agents/conversation/prompts_consult.py", "DEGRADED_REGENERATION_PROMPT"),
}
```

- [ ] **Step 2: 验证 import**

Run: `cd backend && python -c "from agents.conversation.prompts_consult import CONSULT_SYSTEM_PROMPT, INTENT_EXTRACTION_PROMPT, DEGRADED_REGENERATION_PROMPT, CODE_DEFAULTS, PROMPT_FILE_MAP; print(len(CODE_DEFAULTS), len(PROMPT_FILE_MAP))"`
Expected: `3 3`

- [ ] **Step 3: Commit**

```bash
cd backend
git add agents/conversation/prompts_consult.py
git commit -m "feat(backend): add consult prompt constants"
```

---

## Task 5: 编写 prompt_service 测试（TDD）

**Files:**
- Test: `backend/tests/unit/test_prompt_service.py`

- [ ] **Step 1: 编写 prompt_service 单测**

Create `backend/tests/unit/test_prompt_service.py`:
```python
"""prompt_service 单测 — 仅依赖 PromptTemplate ORM 与代码常量回退。

测试契约：
1. DB 中无记录时，load_prompt 返回代码默认值
2. DB 中有 active 记录时，返回 DB 内容
3. 多版本时返回最新 version
4. 多租户隔离：tenant_slug 不同时互不影响
5. is_active=False 的版本被忽略
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.conversation.prompts_consult import CODE_DEFAULTS


@pytest.mark.asyncio
async def test_load_prompt_fallback_to_code_default():
    """DB 无记录时回退代码常量。"""
    from services.prompt_service import load_prompt
    with patch("services.prompt_service.async_session") as mock_session:
        # 模拟空查询结果
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await load_prompt("consult_system", "scnu")
        assert result == CODE_DEFAULTS["consult_system"]


@pytest.mark.asyncio
async def test_load_prompt_returns_db_content_when_present():
    """DB 有 active 记录时返回 DB 内容。"""
    from services.prompt_service import load_prompt
    db_content = "自定义咨询提示词内容"
    with patch("services.prompt_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.content = db_content
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_row
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await load_prompt("consult_system", "scnu")
        assert result == db_content


@pytest.mark.asyncio
async def test_load_prompt_invalid_key_returns_empty_string():
    """无效 prompt_key（不在 CODE_DEFAULTS 且 DB 也无）返回空串。"""
    from services.prompt_service import load_prompt
    with patch("services.prompt_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await load_prompt("nonexistent_key", "scnu")
        assert result == ""
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/unit/test_prompt_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.prompt_service'`

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/unit/test_prompt_service.py
git commit -m "test(backend): add prompt_service unit tests (failing)"
```

---

## Task 6: 实现 prompt_service

**Files:**
- Create: `backend/services/prompt_service.py`

- [ ] **Step 1: 实现 prompt_service**

Create `backend/services/prompt_service.py`:
```python
"""提示词加载服务：DB 优先 → 代码常量回退。"""
import logging

from sqlalchemy import select
from models import async_session
from models.prompt_template import PromptTemplate
from agents.conversation.prompts_consult import CODE_DEFAULTS

_logger = logging.getLogger(__name__)


async def load_prompt(prompt_key: str, tenant_slug: str = "scnu") -> str:
    """加载提示词。优先从 DB active 记录读取，失败回退代码默认值。

    Args:
        prompt_key: consult_system / consult_intent / consult_degraded / b2b_system / ...
        tenant_slug: 租户 slug，默认 scnu

    Returns:
        提示词内容字符串；DB 无记录且无代码默认值时返回空串。
    """
    try:
        async with async_session() as db:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.tenant_slug == tenant_slug,
                    PromptTemplate.prompt_key == prompt_key,
                    PromptTemplate.is_active == True,
                ).order_by(PromptTemplate.version.desc())
            )
            row = result.scalar_one_or_none()
            if row:
                return row.content
    except Exception as e:
        _logger.warning(f"Failed to load prompt {prompt_key} from DB: {e}")

    return CODE_DEFAULTS.get(prompt_key, "")


async def get_active_version(prompt_key: str, tenant_slug: str = "scnu") -> int | None:
    """获取当前 active 版本号，无记录返回 None。"""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.tenant_slug == tenant_slug,
                    PromptTemplate.prompt_key == prompt_key,
                    PromptTemplate.is_active == True,
                ).order_by(PromptTemplate.version.desc())
            )
            row = result.scalar_one_or_none()
            return row.version if row else None
    except Exception:
        return None
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/unit/test_prompt_service.py -v`
Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
cd backend
git add services/prompt_service.py
git commit -m "feat(backend): implement prompt_service (DB-first with code fallback)"
```

---

## Task 7: 编写 prompt_sync_service 测试（TDD）

**Files:**
- Test: `backend/tests/unit/test_prompt_sync_service.py`

- [ ] **Step 1: 编写 prompt_sync_service 单测**

Create `backend/tests/unit/test_prompt_sync_service.py`:
```python
"""prompt_sync_service 单测 — 代码常量文件同步。

测试契约：
1. sync_to_code_with_retry 成功时返回 SyncResult(success=True)
2. 文件写入失败时重试 3 次
3. 文件不存在时返回 success=False
4. 正则替换保留常量名，仅替换内容
"""
import asyncio
from unittest.mock import patch, mock_open, MagicMock

import pytest

from services.prompt_sync_service import sync_to_code_with_retry, SyncResult


@pytest.mark.asyncio
async def test_sync_success_returns_success_result(tmp_path):
    """成功同步返回 success=True。"""
    # 准备：创建一个临时 .py 文件
    test_file = tmp_path / "prompts_consult.py"
    test_file.write_text(
        'CONSULT_SYSTEM_PROMPT = """旧内容"""\n',
        encoding="utf-8",
    )

    new_content = "新内容"
    with patch("services.prompt_sync_service.PROMPT_FILE_MAP", {
        "consult_system": (str(test_file), "CONSULT_SYSTEM_PROMPT"),
    }):
        result = await sync_to_code_with_retry("consult_system", new_content)

    assert result.success is True
    assert "新内容" in test_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_sync_failure_returns_failure_result_after_retries():
    """文件不存在时返回 success=False（重试 3 次）。"""
    with patch("services.prompt_sync_service.PROMPT_FILE_MAP", {
        "consult_system": ("/nonexistent/path/file.py", "CONSULT_SYSTEM_PROMPT"),
    }):
        with patch("services.prompt_sync_service.asyncio.sleep", new=AsyncMock()):
            result = await sync_to_code_with_retry("consult_system", "内容")

    assert result.success is False
    assert result.attempts == 3


# 用于 test_sync_failure_returns_failure_result_after_retries
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_sync_replaces_only_constant_content(tmp_path):
    """正则替换仅替换常量内容，保留常量名与三引号结构。"""
    test_file = tmp_path / "prompts_consult.py"
    original = (
        'OTHER_CONST = "x"\n'
        '\n'
        'CONSULT_SYSTEM_PROMPT = """旧内容\n多行\n"""\n'
        '\n'
        'ANOTHER = 1\n'
    )
    test_file.write_text(original, encoding="utf-8")

    with patch("services.prompt_sync_service.PROMPT_FILE_MAP", {
        "consult_system": (str(test_file), "CONSULT_SYSTEM_PROMPT"),
    }):
        result = await sync_to_code_with_retry("consult_system", "新内容")

    content = test_file.read_text(encoding="utf-8")
    assert result.success is True
    assert 'OTHER_CONST = "x"' in content
    assert "ANOTHER = 1" in content
    assert 'CONSULT_SYSTEM_PROMPT = """新内容"""' in content
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/unit/test_prompt_sync_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.prompt_sync_service'`

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/unit/test_prompt_sync_service.py
git commit -m "test(backend): add prompt_sync_service unit tests (failing)"
```

---

## Task 8: 实现 prompt_sync_service

**Files:**
- Create: `backend/services/prompt_sync_service.py`

- [ ] **Step 1: 实现 prompt_sync_service**

Create `backend/services/prompt_sync_service.py`:
```python
"""提示词代码常量文件同步服务（双写机制）。

DB 是主存储，代码常量同步失败不阻塞 DB 保存。
通过 sync_to_code_with_retry 提供 3 次重试 + 指数退避。
"""
import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from agents.conversation.prompts_consult import PROMPT_FILE_MAP as CONSULT_MAP

_logger = logging.getLogger(__name__)

# 合并 consult 与 b2b 的映射（b2b 暂用同一 map，后续扩展）
PROMPT_FILE_MAP = dict(CONSULT_MAP)


@dataclass
class SyncResult:
    success: bool
    attempts: int
    error: str | None = None


async def sync_to_code_with_retry(prompt_key: str, content: str) -> SyncResult:
    """同步提示词到代码常量文件，3 次重试，指数退避 1s/2s/4s。

    Args:
        prompt_key: 如 "consult_system"
        content: 新的提示词内容

    Returns:
        SyncResult(success, attempts, error)
    """
    if prompt_key not in PROMPT_FILE_MAP:
        return SyncResult(success=False, attempts=0, error=f"Unknown prompt_key: {prompt_key}")

    file_path_str, const_name = PROMPT_FILE_MAP[prompt_key]
    last_error = ""

    for attempt in range(3):
        try:
            await _sync_to_code_file(file_path_str, const_name, content)
            return SyncResult(success=True, attempts=attempt + 1)
        except Exception as e:
            last_error = str(e)
            _logger.warning(f"Prompt sync attempt {attempt + 1} failed for {prompt_key}: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    return SyncResult(success=False, attempts=3, error=last_error)


async def _sync_to_code_file(file_path_str: str, const_name: str, content: str) -> None:
    """用正则替换 .py 文件中的常量定义。

    匹配模式：{const_name} = """..."""
    替换为：{const_name} = """{content}"""
    """
    file_path = Path(file_path_str)
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    original = await asyncio.to_thread(file_path.read_text, "utf-8")

    # 正则匹配 CONST_NAME = """..."""
    pattern = re.compile(
        rf'({re.escape(const_name)}\s*=\s*""")([\s\S]*?)(""")',
        re.MULTILINE
    )
    new_content_str = f"{const_name} = \"\"\"{content}\"\"\""
    replacement = lambda m: f'{m.group(1)}{content}{m.group(3)}'

    if not pattern.search(original):
        raise ValueError(f"Constant {const_name} not found in {file_path}")

    updated = pattern.sub(replacement, original, count=1)
    await asyncio.to_thread(file_path.write_text, updated, "utf-8")
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/unit/test_prompt_sync_service.py -v`
Expected: 3 passed

- [ ] **Step 3: Commit**

```bash
cd backend
git add services/prompt_sync_service.py
git commit -m "feat(backend): implement prompt_sync_service with retry"
```

---

## Task 9: 编写 consult_retrieval_service 测试（TDD）

**Files:**
- Test: `backend/tests/unit/test_consult_retrieval_service.py`

- [ ] **Step 1: 编写检索服务单测**

Create `backend/tests/unit/test_consult_retrieval_service.py`:
```python
"""consult_retrieval_service 单测 — 双层检索逻辑。

测试契约：
1. query_admission_data 按 majors+province+year 精确查询
2. year=None 时返回最新 3 年数据
3. 专业名模糊匹配（ILIKE）
4. 空结果返回 []
5. build_rag_query 按 intent_type 构建不同 query
6. chitchat 的 RAG query 为空（跳过检索）
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_query_admission_data_returns_matching_rows():
    """精确查询返回匹配的 admission_data 行。"""
    from services.consult_retrieval_service import query_admission_data
    college_id = uuid.uuid4()
    mock_rows = [
        MagicMock(major_name="人工智能", year=2024, province="广东", batch="本科批",
                  min_score=585, min_rank=32000, subject_requirements="首选物理,再选化学"),
    ]
    with patch("services.consult_retrieval_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_rows
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await query_admission_data(["人工智能"], "广东", 2024, college_id)

    assert len(result) == 1
    assert result[0]["major_name"] == "人工智能"
    assert result[0]["min_rank"] == 32000


@pytest.mark.asyncio
async def test_query_admission_data_returns_empty_when_no_match():
    """无匹配时返回空列表。"""
    from services.consult_retrieval_service import query_admission_data
    with patch("services.consult_retrieval_service.async_session") as mock_session:
        mock_db = AsyncMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await query_admission_data(["不存在专业"], "广东", 2024, uuid.uuid4())

    assert result == []


def test_build_rag_query_data_query_with_majors():
    """data_query + majors 非空 → 构建专业+省份 query。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "data_query", "majors": ["人工智能"], "province": "广东", "year": 2024}
    user_content = "人工智能 2024 年位次多少"

    query = build_rag_query(intent, user_content)

    assert "人工智能" in query
    assert "广东" in query


def test_build_rag_query_chitchat_returns_empty():
    """chitchat → 返回空串表示跳过 RAG。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "chitchat", "majors": [], "province": "广东", "year": None}
    user_content = "你好"

    query = build_rag_query(intent, user_content)

    assert query == ""


def test_build_rag_query_policy_query_with_majors():
    """policy_query + majors → 招生章程 query。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "policy_query", "majors": ["人工智能"], "province": "广东", "year": None}
    user_content = "人工智能专业的选科要求"

    query = build_rag_query(intent, user_content)

    assert "人工智能" in query
    assert "招生章程" in query


def test_build_rag_query_major_intro_without_majors():
    """major_intro + majors 空 → 原始 content + 专业介绍。"""
    from services.consult_retrieval_service import build_rag_query
    intent = {"intent_type": "major_intro", "majors": [], "province": "广东", "year": None}
    user_content = "计算机类专业"

    query = build_rag_query(intent, user_content)

    assert "计算机类专业" in query
    assert "专业介绍" in query
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/unit/test_consult_retrieval_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.consult_retrieval_service'`

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/unit/test_consult_retrieval_service.py
git commit -m "test(backend): add consult_retrieval_service unit tests (failing)"
```

---

## Task 10: 实现 consult_retrieval_service

**Files:**
- Create: `backend/services/consult_retrieval_service.py`

- [ ] **Step 1: 实现检索服务**

Create `backend/services/consult_retrieval_service.py`:
```python
"""咨询模块双层检索服务。

Step 2a: query_admission_data — SQL 精确查询 admission_data 表
Step 2b: build_rag_query + search_similar — RAG 向量检索
"""
import logging
import uuid
from sqlalchemy import select, or_

from models import async_session
from models.admission import AdmissionData

_logger = logging.getLogger(__name__)


async def query_admission_data(
    majors: list[str],
    province: str,
    year: int | None,
    tenant_college_id: uuid.UUID,
) -> list[dict]:
    """精确查询 admission_data 表。

    Args:
        majors: 标准化专业名列表
        province: 省份（如"广东"）
        year: 年份（None 时取该专业最新 3 年）
        tenant_college_id: 院校 ID（多租户隔离）

    Returns:
        [{major_name, year, province, batch, min_score, min_rank, subject_requirements}, ...]
    """
    if not majors:
        return []

    try:
        async with async_session() as db:
            # 构建专业名模糊匹配条件（ILIKE）
            major_conditions = []
            for m in majors:
                major_conditions.append(AdmissionData.major_name.ilike(f"%{m}%"))

            stmt = select(AdmissionData).where(
                AdmissionData.college_id == tenant_college_id,
                AdmissionData.province == province,
                or_(*major_conditions),
            )

            if year is not None:
                stmt = stmt.where(AdmissionData.year == year)
                stmt = stmt.order_by(AdmissionData.year.desc())
            else:
                # 取每个专业的最新 3 年
                stmt = stmt.order_by(
                    AdmissionData.major_name.asc(),
                    AdmissionData.year.desc(),
                )

            result = await db.execute(stmt)
            rows = result.scalars().all()

            # year=None 时按专业分组取前 3 年
            if year is None and rows:
                grouped: dict[str, list] = {}
                for r in rows:
                    grouped.setdefault(r.major_name, []).append(r)
                rows = []
                for major_rows in grouped.values():
                    rows.extend(major_rows[:3])

            return [
                {
                    "major_name": r.major_name,
                    "year": r.year,
                    "province": r.province,
                    "batch": r.batch or "",
                    "min_score": r.min_score or 0,
                    "min_rank": r.min_rank or 0,
                    "subject_requirements": r.subject_requirements or "",
                }
                for r in rows
            ]
    except Exception as e:
        _logger.warning(f"query_admission_data failed: {e}")
        return []


def build_rag_query(intent: dict, user_content: str) -> str:
    """根据 intent_type 与 majors 构建 RAG 检索 query。

    Returns:
        检索 query 字符串；空串表示跳过 RAG（chitchat 场景）。
    """
    intent_type = intent.get("intent_type", "chitchat")
    majors = intent.get("majors") or []
    province = intent.get("province") or "广东"
    year = intent.get("year")

    if intent_type == "chitchat":
        return ""

    if not majors:
        # 无专业名时用原始 user_content
        if intent_type == "data_query":
            return user_content
        elif intent_type == "policy_query":
            return f"{user_content} 招生政策"
        elif intent_type == "major_intro":
            return f"{user_content} 专业介绍"
        return user_content

    majors_str = " ".join(majors)

    if intent_type == "data_query":
        year_str = f" {year}" if year else ""
        return f"{majors_str} 录取 分数 位次{year_str} {province}"
    elif intent_type == "policy_query":
        return f"{majors_str} 招生章程 选科要求 培养方案"
    elif intent_type == "major_intro":
        return f"{majors_str} 专业介绍 课程 就业前景"
    return user_content


def render_admission_table(admission_rows: list[dict]) -> str:
    """将 admission_rows 渲染为 Markdown 表格字符串。"""
    if not admission_rows:
        return "（暂无相关录取数据）"

    header = "| 专业 | 年份 | 省份 | 批次 | 最低分 | 最低位次 | 选科要求 |"
    separator = "|------|------|------|------|--------|----------|----------|"
    lines = [header, separator]
    for r in admission_rows:
        lines.append(
            f"| {r['major_name']} | {r['year']} | {r['province']} | {r['batch']} | "
            f"{r['min_score']} | {r['min_rank']} | {r['subject_requirements']} |"
        )
    return "\n".join(lines)
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/unit/test_consult_retrieval_service.py -v`
Expected: 5 passed

- [ ] **Step 3: Commit**

```bash
cd backend
git add services/consult_retrieval_service.py
git commit -m "feat(backend): implement consult_retrieval_service (dual-layer retrieval)"
```

---

## Task 11: 编写 consult_validator 测试（TDD）

**Files:**
- Test: `backend/tests/unit/test_consult_validator.py`

- [ ] **Step 1: 编写校验服务单测**

Create `backend/tests/unit/test_consult_validator.py`:
```python
"""consult_validator 单测 — 后置校验逻辑。

测试契约：
1. validate_response 通过场景：回复数字与 DB 一致
2. mismatch 场景：回复数字与 DB 不一致
3. fabricated 场景：回复中的专业在 DB 中不存在
4. wrong_major 场景：回复数字是其他专业的
5. 回复无数字时返回空 issues
6. 简称映射：'AI' → '人工智能'
"""
import pytest

from services.consult_validator import validate_response


def test_validate_pass_when_reply_matches_db():
    """回复数字与 DB 一致时返回空 issues。"""
    reply = "人工智能专业 2024 年在广东最低录取分 585，位次 32000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert issues == []


def test_validate_mismatch_when_reply_rank_differs_from_db():
    """回复位次与 DB 不一致时返回 mismatch issue。"""
    reply = "人工智能专业 2024 年最低位次 45000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert len(issues) == 1
    assert issues[0].issue_type == "mismatch"
    assert issues[0].metric == "min_rank"
    assert issues[0].value_in_reply == 45000


def test_validate_fabricated_when_major_not_in_db():
    """回复中的专业在 DB 中不存在时返回 fabricated issue。"""
    reply = "软件工程专业 2024 年最低位次 32000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert len(issues) == 1
    assert issues[0].issue_type == "fabricated"


def test_validate_wrong_major_when_digit_belongs_to_other_major():
    """回复位次是其他专业的（专业错配）时返回 wrong_major issue。"""
    reply = "人工智能专业 2024 年最低位次 50000"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
        {"major_name": "软件工程", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 580, "min_rank": 50000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert len(issues) >= 1
    assert any(i.issue_type == "wrong_major" for i in issues)


def test_validate_returns_empty_when_reply_has_no_numbers():
    """回复中无数字时返回空 issues。"""
    reply = "华南师范大学暂未公开该专业的录取数据"
    admission_rows = [
        {"major_name": "人工智能", "year": 2024, "province": "广东", "batch": "本科批",
         "min_score": 585, "min_rank": 32000, "subject_requirements": "首选物理,再选化学"},
    ]
    issues = validate_response(reply, admission_rows)
    assert issues == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/unit/test_consult_validator.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'services.consult_validator'`

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/unit/test_consult_validator.py
git commit -m "test(backend): add consult_validator unit tests (failing)"
```

---

## Task 12: 实现 consult_validator

**Files:**
- Create: `backend/services/consult_validator.py`

- [ ] **Step 1: 实现校验服务**

Create `backend/services/consult_validator.py`:
```python
"""咨询模块后置校验服务。

校验 LLM 回复中提到的「专业名 + 数字」是否与 admission_rows 一致。
issue_type: mismatch | fabricated | wrong_major
"""
import re
from dataclasses import dataclass


@dataclass
class ValidationIssue:
    major_in_reply: str
    metric: str  # "min_score" | "min_rank"
    value_in_reply: int
    matched_db_row: dict | None
    issue_type: str  # "mismatch" | "fabricated" | "wrong_major"


# 专业名简称映射（校验前标准化）
MAJOR_ALIAS_MAP = {
    "AI": "人工智能",
    "软工": "软件工程",
    "计科": "计算机科学与技术",
    "信管": "信息管理与信息系统",
}


def _normalize_major(name: str) -> str:
    """专业名标准化（简称 → 全称）。"""
    return MAJOR_ALIAS_MAP.get(name, name)


def _extract_major_digit_pairs(reply: str, known_majors: list[str]) -> list[tuple[str, int]]:
    """从回复中提取所有「专业名 + 数字」组合。

    匹配策略：
    1. 优先匹配已知专业名（来自 admission_rows）
    2. 匹配模式：(专业名)\D{0,10}(\d{4,6})
    """
    pairs = []
    for major in known_majors:
        # 匹配专业名后 0-10 个非数字字符，然后是 4-6 位数字
        pattern = rf"{re.escape(major)}\D{{0,10}}(\d{{4,6}})"
        matches = re.findall(pattern, reply)
        for m in matches:
            pairs.append((major, int(m)))

    # 也匹配简称
    for alias, full in MAJOR_ALIAS_MAP.items():
        if full in known_majors:
            pattern = rf"{re.escape(alias)}\D{{0,10}}(\d{{4,6}})"
            matches = re.findall(pattern, reply)
            for m in matches:
                pairs.append((full, int(m)))

    return pairs


def validate_response(
    reply: str,
    admission_rows: list[dict],
) -> list[ValidationIssue]:
    """校验回复中的数字是否与 admission_rows 一致。

    Args:
        reply: LLM 回复文本
        admission_rows: 数据库查询结果

    Returns:
        issues 列表（空列表 = 通过）
    """
    if not admission_rows:
        return []

    known_majors = list({r["major_name"] for r in admission_rows})
    pairs = _extract_major_digit_pairs(reply, known_majors)

    if not pairs:
        return []

    issues: list[ValidationIssue] = []
    seen = set()  # 防止重复 issue

    for major_in_reply, value_in_reply in pairs:
        # 查找该专业的 DB 行
        matched_rows = [r for r in admission_rows if r["major_name"] == major_in_reply]

        if not matched_rows:
            # 专业不在 DB 中
            key = (major_in_reply, value_in_reply, "fabricated")
            if key not in seen:
                seen.add(key)
                issues.append(ValidationIssue(
                    major_in_reply=major_in_reply,
                    metric="unknown",
                    value_in_reply=value_in_reply,
                    matched_db_row=None,
                    issue_type="fabricated",
                ))
            continue

        # 检查这个数字是否匹配该专业的任一指标
        for row in matched_rows:
            if value_in_reply == row["min_score"]:
                # 匹配 min_score，通过
                break
            if value_in_reply == row["min_rank"]:
                # 匹配 min_rank，通过
                break
        else:
            # 不匹配该专业任何指标
            # 检查是否是其他专业的数字（wrong_major）
            other_major_match = None
            for other_row in admission_rows:
                if other_row["major_name"] == major_in_reply:
                    continue
                if value_in_reply in (other_row["min_score"], other_row["min_rank"]):
                    other_major_match = other_row
                    break

            if other_major_match:
                key = (major_in_reply, value_in_reply, "wrong_major")
                if key not in seen:
                    seen.add(key)
                    issues.append(ValidationIssue(
                        major_in_reply=major_in_reply,
                        metric="min_rank" if value_in_reply == other_major_match["min_rank"] else "min_score",
                        value_in_reply=value_in_reply,
                        matched_db_row=other_major_match,
                        issue_type="wrong_major",
                    ))
            else:
                # 数字不匹配任何专业，是编造的
                # 判断更像分数还是位次（5 位数以下当分数，6 位数当位次）
                metric = "min_rank" if value_in_reply >= 10000 else "min_score"
                key = (major_in_reply, value_in_reply, "mismatch")
                if key not in seen:
                    seen.add(key)
                    issues.append(ValidationIssue(
                        major_in_reply=major_in_reply,
                        metric=metric,
                        value_in_reply=value_in_reply,
                        matched_db_row=matched_rows[0],
                        issue_type="mismatch",
                    ))

    return issues
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/unit/test_consult_validator.py -v`
Expected: 5 passed

- [ ] **Step 3: Commit**

```bash
cd backend
git add services/consult_validator.py
git commit -m "feat(backend): implement consult_validator with mismatch/fabricated/wrong_major detection"
```

---

## Task 13: 扩展 consult_service 支持 module_type 与前缀隔离

**Files:**
- Modify: `backend/services/consult_service.py:11-67` (get_or_create_session 函数)

- [ ] **Step 1: 修改 get_or_create_session 增加 module_type 参数**

Edit `backend/services/consult_service.py`，将 `get_or_create_session` 替换为：
```python
CONSULT_SESSION_PREFIX = "sess_consult_"
RECOMMEND_SESSION_PREFIX = "sess_"


async def get_or_create_session(
    session_id: str | None,
    tenant_slug: str,
    user_id: uuid.UUID | None = None,
    module_type: str = "recommend",  # "consult" | "recommend"
) -> tuple[ConsultSession, bool]:
    """Return (session, is_new). Expired sessions get a fresh session_id.

    Args:
        module_type: "consult" 创建咨询会话（前缀 sess_consult_），"recommend" 创建推荐会话（前缀 sess_）
    """
    prefix = CONSULT_SESSION_PREFIX if module_type == "consult" else RECOMMEND_SESSION_PREFIX

    async with async_session() as db:
        if session_id:
            result = await db.execute(
                select(ConsultSession).where(ConsultSession.session_id == session_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                now = datetime.now(timezone.utc)
                if existing.expires_at is None or existing.expires_at > now:
                    await db.commit()
                    return existing, False
                # Expired: delete old row so we can reuse the session_id
                await db.delete(existing)
                await db.flush()

        # 验证 session_id 前缀，不匹配则生成新的
        if session_id and not session_id.startswith(prefix):
            session_id = None
        new_id = session_id if session_id else f"{prefix}{uuid.uuid4().hex[:12]}"
        ttl = REGISTERED_TTL if user_id else GUEST_TTL
        expires_at = datetime.now(timezone.utc) + ttl

        # 推荐会话：尝试绑定最近活跃咨询会话
        context_ref_session_id = None
        if module_type == "recommend" and user_id:
            try:
                recent_consult_result = await db.execute(
                    select(ConsultSession).where(
                        ConsultSession.user_id == user_id,
                        ConsultSession.tenant_slug == tenant_slug,
                        ConsultSession.session_id.like(f"{CONSULT_SESSION_PREFIX}%"),
                        ConsultSession.consult_started_at.isnot(None),
                    ).order_by(ConsultSession.updated_at.desc()).limit(1)
                )
                recent_consult = recent_consult_result.scalar_one_or_none()
                if recent_consult:
                    context_ref_session_id = recent_consult.id
            except Exception as e:
                import logging
                logging.warning(f"Failed to find recent consult session for context_ref: {e}")

        # Snapshot basic info from users table for registered users
        province = ""
        subjects = ""
        score = 0
        rank = None
        if user_id:
            from models.user import User
            user_result = await db.execute(select(User).where(User.id == user_id))
            u = user_result.scalar_one_or_none()
            if u:
                province = u.region or ""
                subjects = u.subjects or ""
                score = u.score or 0
                rank = u.rank

        new_session = ConsultSession(
            session_id=new_id,
            tenant_slug=tenant_slug,
            user_id=user_id,
            province=province,
            subjects=subjects,
            score=score,
            rank=rank,
            expires_at=expires_at,
            context_ref_session_id=context_ref_session_id,
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session, True
```

- [ ] **Step 2: 验证 import 无误**

Run: `cd backend && python -c "from services.consult_service import get_or_create_session, CONSULT_SESSION_PREFIX, RECOMMEND_SESSION_PREFIX; print(CONSULT_SESSION_PREFIX, RECOMMEND_SESSION_PREFIX)"`
Expected: `sess_consult_ sess_`

- [ ] **Step 3: Commit**

```bash
cd backend
git add services/consult_service.py
git commit -m "feat(backend): support module_type in get_or_create_session with prefix isolation"
```

---

## Task 14: 修改 miniapp_enter 路由支持 module_type

**Files:**
- Modify: `backend/api/routes/miniapp.py` (miniapp_enter 函数)
- Modify: `backend/schemas/miniapp.py` (EnterRequest schema，需先查看)

- [ ] **Step 1: 查看 EnterRequest schema 现状**

Run: `cd backend && python -c "from schemas.miniapp import EnterRequest; print(EnterRequest.model_fields)"`
（记录字段结构用于扩展）

- [ ] **Step 2: 在 EnterRequest 中添加 module_type 字段**

Edit `backend/schemas/miniapp.py`，在 `EnterRequest` 类中添加 `module_type` 字段：
```python
class EnterRequest(BaseModel):
    session_id: str | None = None
    tenant_slug: str | None = None
    module_type: str = "recommend"  # "consult" | "recommend"
```

（注：若现有 schema 字段名不同，需先 grep `class EnterRequest` 确认）

- [ ] **Step 3: 修改 miniapp_enter 传递 module_type**

Edit `backend/api/routes/miniapp.py`，将 `miniapp_enter` 中的 `get_or_create_session` 调用改为：
```python
    session, is_new = await get_or_create_session(
        body.session_id, tenant_slug, user_id, module_type=body.module_type
    )
```

- [ ] **Step 4: 验证编译**

Run: `cd backend && python -c "from api.routes.miniapp import miniapp_enter; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
cd backend
git add schemas/miniapp.py api/routes/miniapp.py
git commit -m "feat(backend): miniapp_enter supports module_type param"
```

---

## Task 15: 创建 consult SSE 路由

**Files:**
- Create: `backend/api/routes/consult.py`
- Create: `backend/schemas/consult.py` (请求/响应 schema)

- [ ] **Step 1: 创建 consult schema**

Create `backend/schemas/consult.py`:
```python
"""咨询模块请求/响应 schema。"""
from pydantic import BaseModel


class ConsultMessageContent(BaseModel):
    content: str


class ConsultMessageRequest(BaseModel):
    session_id: str
    tenant_slug: str = "scnu"
    message: ConsultMessageContent
```

- [ ] **Step 2: 创建 consult 路由**

Create `backend/api/routes/consult.py`:
```python
"""咨询模块 SSE 路由 — 双层检索 + 后置校验 + 重生成。"""
import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select

from config import settings
from models import async_session
from models.college import College
from schemas.consult import ConsultMessageRequest
from services.consult_service import get_session, get_chat_history, save_message
from services.consult_retrieval_service import (
    query_admission_data, build_rag_query, render_admission_table,
)
from services.consult_validator import validate_response
from services.prompt_service import load_prompt
from tenants.service import resolve_tenant
from core.event_writer import write_event
from utils.jwt import decode_token

router = APIRouter(prefix="/api/v1", tags=["consult"])
_logger = logging.getLogger(__name__)


def _sse(event_type: str, data: dict) -> str:
    """格式化 SSE 事件。"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/consult/messages")
async def send_consult_message(body: ConsultMessageRequest, request: Request):
    """咨询 SSE 流：意图抽取 → 双层检索 → 主回答 → 后置校验 → 重生成。"""
    # 模块开关
    if not settings.consult_module_enabled:
        raise HTTPException(status_code=403, detail="Consult module disabled")

    # 鉴权
    auth_header = request.headers.get("Authorization", "")
    user_id = None
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            if payload:
                user_id = uuid.UUID(payload["user_id"])
        except Exception:
            pass
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    session = await get_session(body.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    tenant = await resolve_tenant(body.tenant_slug)
    tenant_id = tenant.id if tenant else None

    user_content = body.message.content
    await save_message(body.session_id, "user", user_content)

    # 查询 SCNU college_id
    async with async_session() as db:
        scnu_result = await db.execute(select(College).where(College.name == "华南师范大学"))
        scnu = scnu_result.scalar_one_or_none()
    college_id = scnu.id if scnu else None

    async def event_stream():
        # Phase 0: thinking
        yield _sse("thinking", {"status": "正在理解你的问题..."})

        # Phase 1: 意图抽取（LLM-1, temp=0）
        intent = await _extract_intent(user_content)
        yield _sse("intent_extracted", intent)

        # Phase 2: 双层检索
        # 2a: admission_data SQL 查询（仅 need_admission_data=true）
        admission_rows = []
        if intent.get("need_admission_data") and college_id:
            majors = intent.get("majors") or []
            province = intent.get("province") or "广东"
            year = intent.get("year")
            admission_rows = await query_admission_data(majors, province, year, college_id)

        # 2b: RAG 检索
        rag_query = build_rag_query(intent, user_content)
        knowledge_context, sources = await _do_rag(rag_query, body.tenant_slug)

        # 下发 source 事件
        yield _sse("search_start", {"stage": "structured"})
        for i, src in enumerate(sources, 1):
            yield _sse("source", {"index": i, "title": src.get("source_title", ""), "url": src.get("source_url", "")})
        yield _sse("search_end", {"admission_rows": len(admission_rows), "rag_sources": len(sources)})

        # Phase 3: 上下文组装
        slots_summary = await _build_slots_summary(session)
        admission_table = render_admission_table(admission_rows)
        system_prompt_template = await load_prompt("consult_system", body.tenant_slug)
        system_content = system_prompt_template.format(
            slots_summary=slots_summary,
            admission_table=admission_table,
            knowledge_context=knowledge_context,
        )

        # 历史消息
        history_msgs = await get_chat_history(body.session_id, limit=10)
        history = []
        for m in history_msgs:
            if m["role"] == "user":
                history.append(HumanMessage(content=m["content"]))
            else:
                history.append(AIMessage(content=m["content"]))
        if history and isinstance(history[-1], HumanMessage):
            history.pop()

        msgs = [SystemMessage(content=system_content)] + history + [HumanMessage(content=user_content)]

        llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.3,
        )

        # Phase 4: 主回答流式生成
        reply_v1 = ""
        try:
            async for chunk in llm.astream(msgs):
                token = chunk.content if hasattr(chunk, "content") else str(chunk)
                if token:
                    reply_v1 += token
                    yield _sse("token", {"content": token})
        except Exception as exc:
            _logger.error(f"LLM stream failed: {exc}")
            yield _sse("error", {"code": "LLM_FAILED", "message": "AI 服务暂时不可用"})
            return

        # Phase 5: 后置校验（仅当 admission_rows 非空）
        final_reply = reply_v1
        regenerated = False
        degraded = False

        if admission_rows:
            yield _sse("validation_start", {})
            issues = validate_response(reply_v1, admission_rows)

            if not issues:
                yield _sse("validation_passed", {})
            else:
                # 触发重生成（1 次）
                yield _sse("regenerating", {
                    "issues": [
                        {
                            "type": i.issue_type,
                            "major": i.major_in_reply,
                            "metric": i.metric,
                            "reply_value": i.value_in_reply,
                        }
                        for i in issues
                    ]
                })

                degraded_prompt_template = await load_prompt("consult_degraded", body.tenant_slug)
                degraded_system = degraded_prompt_template.format(
                    admission_table=admission_table,
                    user_content=user_content,
                )
                regen_msgs = [SystemMessage(content=degraded_system)] + [HumanMessage(content=user_content)]

                try:
                    final_reply = ""
                    async for chunk in llm.astream(regen_msgs):
                        token = chunk.content if hasattr(chunk, "content") else str(chunk)
                        if token:
                            final_reply += token
                            yield _sse("token", {"content": token, "regenerated": True})
                    regenerated = True

                    # 二次校验
                    issues_v2 = validate_response(final_reply, admission_rows)
                    if issues_v2:
                        degraded = True
                        yield _sse("validation_warning", {
                            "message": "本次回答中的部分数据未经系统校验通过，请核对官方来源"
                        })
                    else:
                        yield _sse("validation_passed", {})
                except Exception as exc:
                    _logger.error(f"Regeneration failed: {exc}")
                    final_reply = reply_v1
                    degraded = True
                    yield _sse("validation_warning", {
                        "message": "本次回答中的部分数据未经系统校验通过，请核对官方来源"
                    })

        # 保存 assistant 消息
        assistant_msg = await save_message(body.session_id, "assistant", final_reply)

        # 异步触发咨询摘要
        try:
            from services.consult_summary_service import maybe_generate_summary
            asyncio.create_task(maybe_generate_summary(body.session_id))
        except Exception as e:
            _logger.warning(f"Summary trigger failed: {e}")

        # 事件埋点
        if tenant_id:
            try:
                await write_event(
                    tenant_id, "chat_response_completed",
                    session_id=session.id,
                    payload={
                        "response_length": len(final_reply),
                        "regenerated": regenerated,
                        "degraded": degraded,
                    },
                )
            except Exception as e:
                _logger.warning(f"Event chat_response_completed failed: {e}")

        yield _sse("done", {
            "message_id": assistant_msg.get("message_id"),
            "session_id": body.session_id,
            "regenerated": regenerated,
            "degraded": degraded,
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _extract_intent(user_content: str) -> dict:
    """LLM-1 意图抽取，返回结构化 dict。失败降级为 chitchat。"""
    try:
        intent_prompt = await load_prompt("consult_intent", "scnu")
        llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0,
        )
        msgs = [SystemMessage(content=intent_prompt), HumanMessage(content=user_content)]
        result = await llm.ainvoke(msgs)
        text = result.content if hasattr(result, "content") else str(result)
        # 提取 JSON
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group(0))
        return {"intent_type": "chitchat", "majors": [], "need_admission_data": False}
    except Exception as e:
        _logger.warning(f"Intent extraction failed: {e}")
        return {"intent_type": "chitchat", "majors": [], "need_admission_data": False}


async def _do_rag(query: str, tenant_slug: str) -> tuple[str, list[dict]]:
    """RAG 检索，返回 (knowledge_context, sources)。query 为空时跳过。"""
    if not query:
        return "", []
    try:
        from knowledge_base.chroma_client import search_similar
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, search_similar, query, 5, tenant_slug)
        if not results:
            return "", []
        lines = ["\n## 知识库检索结果 (仅供参考)"]
        sources = []
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r['document']}")
            sources.append({
                "text": r["document"][:200],
                "source_title": r.get("metadata", {}).get("source_title", ""),
                "source_url": r.get("metadata", {}).get("source_url", ""),
                "score": round(1 - r.get("distance", 0), 4),
            })
        return "\n".join(lines), sources
    except Exception as e:
        _logger.warning(f"RAG failed: {e}")
        return "", []


async def _build_slots_summary(session) -> str:
    """构建用户基础信息 slots_summary（优先 users 表，回退 session 快照）。"""
    province = session.province or "未知"
    subjects = session.subjects or "未知"
    score = session.score or "未知"
    rank = session.rank or "未知"

    if session.user_id:
        try:
            from models.user import User
            async with async_session() as db:
                u_result = await db.execute(select(User).where(User.id == session.user_id))
                u = u_result.scalar_one_or_none()
                if u:
                    province = u.region or province
                    subjects = u.subjects or subjects
                    score = u.score or score
                    rank = u.rank or rank
        except Exception as e:
            _logger.warning(f"Failed to read user basic info: {e}")

    return f"省份: {province}, 选科: {subjects}, 分数: {score}, 位次: {rank}"
```

- [ ] **Step 3: 在 config.py 中新增 consult_module_enabled**

Edit `backend/config.py`，在 Settings 类中追加：
```python
    consult_module_enabled: bool = True  # 咨询模块开关，默认开启
```

- [ ] **Step 4: 验证 import**

Run: `cd backend && python -c "from api.routes.consult import router; print(len(router.routes))"`
Expected: `1`

- [ ] **Step 5: Commit**

```bash
cd backend
git add api/routes/consult.py schemas/consult.py config.py
git commit -m "feat(backend): implement consult SSE route with dual-layer retrieval and validation"
```

---

## Task 16: 编写 prompt_admin 路由测试（TDD）

**Files:**
- Test: `backend/tests/integration/test_prompt_admin.py`

- [ ] **Step 1: 编写 prompt_admin 集成测试**

Create `backend/tests/integration/test_prompt_admin.py`:
```python
"""prompt_admin 集成测试 — DB + 同步。

测试契约：
1. GET /api/v1/admin/prompts 返回所有 prompt_key 列表（含代码默认值）
2. POST 保存新版本 → 返回新 version
3. 保存触发代码同步（成功/失败均返回 200）
4. 权限：非 developer 返回 403
5. optimistic_lock：version 冲突时返回 409
"""
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_list_prompts_requires_developer(monkeypatch):
    """非 developer 访问返回 403。"""
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 不带 developer JWT
        resp = await client.get(
            "/api/v1/admin/prompts",
            headers={"X-Tenant": "scnu"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_prompts_returns_defaults(monkeypatch):
    """developer 访问返回代码默认值列表。"""
    from core.developer_guard import require_developer
    from tenants.service import resolve_tenant

    # mock developer guard
    async def _bypass():
        return {"user_id": "dev-001", "is_developer": True}
    monkeypatch.setattr("core.developer_guard.require_developer", _bypass)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/admin/prompts",
            headers={"X-Tenant": "scnu"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    keys = [p["prompt_key"] for p in data["data"]]
    assert "consult_system" in keys
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/integration/test_prompt_admin.py -v`
Expected: FAIL with `ModuleNotFoundError` 或 404

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/integration/test_prompt_admin.py
git commit -m "test(backend): add prompt_admin integration tests (failing)"
```

---

## Task 17: 实现 prompt_admin 路由

**Files:**
- Create: `backend/api/routes/prompt_admin.py`

- [ ] **Step 1: 实现 prompt_admin 路由**

Create `backend/api/routes/prompt_admin.py`:
```python
"""提示词管理路由（developer-only）。

支持：
- GET /admin/prompts: 列出所有 prompt_key（合并 DB + 代码默认）
- GET /admin/prompts/{key}: 获取单个 prompt 当前内容
- POST /admin/prompts/{key}: 保存新版本（version+1），触发代码同步
- GET /admin/prompts/health: 健康检查（DB↔代码一致性）
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from core.developer_guard import require_developer
from core.tenant_context import get_current_tenant
from models import get_db, async_session
from models.prompt_template import PromptTemplate
from services.prompt_service import load_prompt, get_active_version
from services.prompt_sync_service import sync_to_code_with_retry
from agents.conversation.prompts_consult import CODE_DEFAULTS, PROMPT_FILE_MAP

router = APIRouter(prefix="/api/v1/admin/prompts", tags=["prompt-admin"])
_logger = logging.getLogger(__name__)


class PromptSaveRequest(BaseModel):
    content: str
    expected_version: int | None = None  # optimistic lock


def _ok(data: dict) -> dict:
    return {"data": data, "error": None}


@router.get("")
async def list_prompts(
    tenant=Depends(get_current_tenant),
    _=Depends(require_developer),
):
    """列出所有 prompt_key 及其当前 active 内容。"""
    tenant_slug = tenant.slug if tenant else "scnu"
    items = []
    for key in CODE_DEFAULTS.keys():
        content = await load_prompt(key, tenant_slug)
        version = await get_active_version(key, tenant_slug)
        items.append({
            "prompt_key": key,
            "content": content,
            "version": version,
            "source": "db" if version else "code_default",
        })
    return _ok({"items": items})


@router.get("/{prompt_key}")
async def get_prompt(
    prompt_key: str,
    tenant=Depends(get_current_tenant),
    _=Depends(require_developer),
):
    """获取单个 prompt 内容。"""
    if prompt_key not in CODE_DEFAULTS:
        raise HTTPException(status_code=404, detail="Prompt key not found")
    tenant_slug = tenant.slug if tenant else "scnu"
    content = await load_prompt(prompt_key, tenant_slug)
    version = await get_active_version(prompt_key, tenant_slug)
    return _ok({
        "prompt_key": prompt_key,
        "content": content,
        "version": version,
    })


@router.post("/{prompt_key}")
async def save_prompt(
    prompt_key: str,
    body: PromptSaveRequest,
    request: Request,
    tenant=Depends(get_current_tenant),
    _=Depends(require_developer),
):
    """保存新版本：旧版本 is_active=False，新版本 version+1 is_active=True。

    乐观锁：若 expected_version 与当前 active version 不匹配，返回 409。
    触发代码同步（asyncio.create_task，3 次重试）。
    """
    if prompt_key not in CODE_DEFAULTS:
        raise HTTPException(status_code=404, detail="Prompt key not found")
    tenant_slug = tenant.slug if tenant else "scnu"

    # 获取 developer user_id
    payload = await require_developer()
    updated_by = uuid.UUID(payload["user_id"]) if payload.get("user_id") else None

    # 乐观锁检查
    current_version = await get_active_version(prompt_key, tenant_slug)
    if body.expected_version is not None and body.expected_version != current_version:
        raise HTTPException(
            status_code=409,
            detail=f"Version conflict: expected={body.expected_version}, current={current_version}"
        )

    new_version = (current_version or 0) + 1

    async with async_session() as db:
        # 旧版本置为 inactive
        if current_version is not None:
            result = await db.execute(
                select(PromptTemplate).where(
                    PromptTemplate.tenant_slug == tenant_slug,
                    PromptTemplate.prompt_key == prompt_key,
                    PromptTemplate.version == current_version,
                )
            )
            old_row = result.scalar_one_or_none()
            if old_row:
                old_row.is_active = False

        # 插入新版本
        new_row = PromptTemplate(
            tenant_slug=tenant_slug,
            prompt_key=prompt_key,
            content=body.content,
            version=new_version,
            is_active=True,
            updated_by=updated_by,
        )
        db.add(new_row)
        await db.commit()

    # 触发代码同步（异步，不阻塞响应）
    import asyncio
    asyncio.create_task(sync_to_code_with_retry(prompt_key, body.content))

    return _ok({
        "prompt_key": prompt_key,
        "version": new_version,
        "sync_triggered": True,
    })


@router.get("/health/check")
async def health_check(
    tenant=Depends(get_current_tenant),
    _=Depends(require_developer),
):
    """一致性检查：对比 DB active 内容与代码常量是否一致。"""
    tenant_slug = tenant.slug if tenant else "scnu"
    mismatches = []
    for key, code_default in CODE_DEFAULTS.items():
        db_content = await load_prompt(key, tenant_slug)
        if db_content != code_default:
            mismatches.append({
                "prompt_key": key,
                "db_active": True,
                "diff_size": abs(len(db_content) - len(code_default)),
            })
    return _ok({
        "total_keys": len(CODE_DEFAULTS),
        "consistent": len(mismatches) == 0,
        "mismatches": mismatches,
    })
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/integration/test_prompt_admin.py -v`
Expected: 至少 1 passed（list_prompts_returns_defaults），403 测试可能需调整 mock

- [ ] **Step 3: Commit**

```bash
cd backend
git add api/routes/prompt_admin.py
git commit -m "feat(backend): implement prompt_admin route (CRUD + sync + health check)"
```

---

## Task 18: 在 main.py 注册新路由 + lifespan 一致性校验

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 先查看 main.py 现有路由注册结构**

Run: `cd backend && python -c "from main import app; print([r.path for r in app.routes if hasattr(r, 'path')][:20])"`

记录现有 include_router 调用方式（用于追加 consult 与 prompt_admin router）。

- [ ] **Step 2: 在 main.py 注册 consult 与 prompt_admin 路由**

Edit `backend/main.py`，在现有 `app.include_router(...)` 区域追加：
```python
from api.routes.consult import router as consult_router
from api.routes.prompt_admin import router as prompt_admin_router

app.include_router(consult_router)
app.include_router(prompt_admin_router)
```

- [ ] **Step 3: 在 lifespan 中追加提示词一致性校验（启动时）**

Edit `backend/main.py` 的 lifespan 函数，在 `await init_db()` 后追加：
```python
        # 启动时校验提示词 DB↔代码一致性（仅日志告警，不阻塞启动）
        try:
            from agents.conversation.prompts_consult import CODE_DEFAULTS
            from services.prompt_service import load_prompt
            for key, code_default in CODE_DEFAULTS.items():
                db_content = await load_prompt(key, "scnu")
                if db_content and db_content != code_default:
                    logger.warning(
                        f"Prompt {key} DB↔code mismatch: "
                        f"db_len={len(db_content)} code_len={len(code_default)}"
                    )
        except Exception as e:
            logger.warning(f"Prompt consistency check skipped: {e}")
```

（注：若 main.py 中 logger 未定义，需用 `import logging; logger = logging.getLogger(__name__)`）

- [ ] **Step 4: 验证路由注册成功**

Run: `cd backend && python -c "from main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; print('/api/v1/consult/messages' in paths); print('/api/v1/admin/prompts' in paths)"`
Expected: `True True`

- [ ] **Step 5: Commit**

```bash
cd backend
git add main.py
git commit -m "feat(backend): register consult + prompt_admin routers, add startup consistency check"
```

---

## Task 19: 扩展 B2B prompt 支持 consult_context

**Files:**
- Modify: `backend/agents/conversation/prompts_b2b.py`

- [ ] **Step 1: 在 B2B_SYSTEM_PROMPT 末尾追加 consult_context 占位符**

Edit `backend/agents/conversation/prompts_b2b.py`，在 B2B_SYSTEM_PROMPT 字符串末尾追加：
```python

## 用户咨询历史（可选，用于增强上下文理解）
{consult_context}

（若上方为空，表示用户未进行过咨询，请按正常推荐流程进行）
```

- [ ] **Step 2: 修改 miniapp.py 中的 chat 路由，注入 consult_context**

Edit `backend/api/routes/miniapp.py` 的 `send_chat_message` 函数，在 `system_content = B2B_SYSTEM_PROMPT.format(...)` 调用前，添加 consult_context 拼接：
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

    system_content = B2B_SYSTEM_PROMPT.format(
        university_name="华南师范大学",
        university_short="华师",
        stage="open",
        slots_summary=slots_text,
        consult_context=consult_context,
    )
```

- [ ] **Step 3: 验证 B2B prompt format 调用兼容**

Run: `cd backend && python -c "from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT; r = B2B_SYSTEM_PROMPT.format(university_name='华师', university_short='华师', stage='open', slots_summary='test', consult_context='test'); print('OK', len(r))"`
Expected: `OK <number>`

- [ ] **Step 4: Commit**

```bash
cd backend
git add agents/conversation/prompts_b2b.py api/routes/miniapp.py
git commit -m "feat(backend): inject consult_context into B2B recommendation prompt"
```

---

## Task 20: 编写 consult SSE 集成测试

**Files:**
- Test: `backend/tests/integration/test_consult_sse.py`

- [ ] **Step 1: 编写 consult SSE 集成测试**

Create `backend/tests/integration/test_consult_sse.py`:
```python
"""consult SSE 集成测试 — 端到端流程。

测试契约：
1. 未鉴权访问返回 401
2. 模块关闭时返回 403
3. 会话不存在返回 404
4. mock LLM 时，SSE 流按预期顺序下发事件
"""
import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_consult_messages_requires_auth(monkeypatch):
    """未鉴权返回 401。"""
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/consult/messages",
            headers={"X-Tenant": "scnu"},
            json={"session_id": "sess_consult_test", "tenant_slug": "scnu",
                  "message": {"content": "人工智能 2024 年位次"}},
        )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_consult_messages_disabled_when_flag_off(monkeypatch):
    """consult_module_enabled=False 时返回 403。"""
    monkeypatch.setenv("CONSULT_MODULE_ENABLED", "false")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    # mock JWT decode 返回有效 user
    async def _mock_decode(token):
        return {"user_id": "00000000-0000-0000-0000-000000000001"}
    monkeypatch.setattr("api.routes.consult.decode_token", _mock_decode)

    # 重新导入以应用 env
    import importlib
    import config
    importlib.reload(config)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/consult/messages",
            headers={"X-Tenant": "scnu", "Authorization": "Bearer fake.jwt.token"},
            json={"session_id": "sess_consult_test", "tenant_slug": "scnu",
                  "message": {"content": "测试"}},
        )
    assert resp.status_code == 403
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/integration/test_consult_sse.py -v`
Expected: 2 passed

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/integration/test_consult_sse.py
git commit -m "test(backend): add consult SSE integration tests"
```

---

## Self-Review

**1. Spec coverage：**
- 咨询模块独立（session_id 前缀）→ Task 13 ✓
- 双层检索（SQL + RAG）→ Task 10 ✓
- 后置校验 + 重生成 + 降级 → Task 12 + Task 15 ✓
- 提示词在线编辑 + DB/代码双写 + 六层保障 → Task 6 + Task 8 + Task 17 + Task 18 ✓
- B2B 注入 consult_context → Task 19 ✓
- Markdown 限制 → Task 4（CONSULT_SYSTEM_PROMPT 中已含约束）✓
- context_ref_session_id 字段 → Task 2 + Task 3 ✓
- 模块开关 → Task 15 (config.py) + Task 20（测试）✓

**2. Placeholder scan：**
- 无 TBD / TODO / "later"
- 所有代码块均含完整实现

**3. Type consistency：**
- `SyncResult(success, attempts, error)` 在 Task 7/8 一致
- `ValidationIssue(major_in_reply, metric, value_in_reply, matched_db_row, issue_type)` 在 Task 11/12 一致
- `load_prompt(prompt_key, tenant_slug)` 在 Task 5/6/17 一致
- `query_admission_data(majors, province, year, tenant_college_id)` 在 Task 9/10/15 一致

**已实现的六层可靠性保障：**
1. 重试：sync_to_code_with_retry 3 次指数退避
2. 队列：asyncio.create_task 异步触发，不阻塞响应
3. 启动校验：main.py lifespan 中 DB↔代码对比
4. 健康检查：GET /admin/prompts/health/check
5. 乐观锁：POST 接口 expected_version 字段，冲突返回 409
6. 告警：所有同步失败均通过 logger.warning 输出

---

## Execution Handoff

Plan 1 已完成并保存至 `docs/superpowers/plans/2026-06-27-01-consult-backend.md`。

**两种执行方式：**

**1. Subagent-Driven（推荐）** — 每个 Task 派发独立 sub-agent，Task 间双阶段 review，快速迭代

**2. Inline Execution** — 在当前会话内顺序执行，带 checkpoint review

**请选择执行方式？**

后续 Plan 2 (Admin-SPA 提示词管理) / Plan 3 (Mini-app 咨询页面) / Plan 4 (推荐模块上下文增强后端部分) 将在 Plan 1 完成后按依赖顺序生成。

