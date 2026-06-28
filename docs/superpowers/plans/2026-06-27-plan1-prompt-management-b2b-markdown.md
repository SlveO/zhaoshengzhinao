# Plan 1: 提示词管理补全 + B2B Markdown 约束 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `b2b_system` / `b2b_few_shot` 纳入 admin-spa 在线管理 + 双写机制；为 B2B 提示词加严格纯文本 Markdown 约束；补齐 chat.py 缺失的 consult_context 注入。

**Architecture:** 合并 consult + b2b 两个模块的 CODE_DEFAULTS / PROMPT_FILE_MAP 到 prompt_service 单一来源；prompt_admin、prompt_sync_service、main.py lifespan 全部改从 prompt_service 导入；chat.py 改用 load_prompt 动态加载 B2B 提示词并注入 consult_context/knowledge_context 占位符；前端 prompt.ts 补 2 个 key 标签。

**Tech Stack:** Python 3.11 + FastAPI + SQLAlchemy + LangChain + React 19 + TypeScript + Vite

**Spec:** `docs/superpowers/specs/2026-06-27-consult-recommend-enhance-design.md` 章节 4

---

## 文件结构

### 修改文件
- `backend/agents/conversation/prompts_b2b.py` — 加 Markdown 约束 + consult_context/knowledge_context 占位符 + CODE_DEFAULTS / PROMPT_FILE_MAP
- `backend/services/prompt_service.py` — 合并 consult + b2b 的 CODE_DEFAULTS / PROMPT_FILE_MAP
- `backend/api/routes/prompt_admin.py` — 从 prompt_service 导入合并后的 CODE_DEFAULTS
- `backend/services/prompt_sync_service.py` — 从 prompt_service 导入合并后的 PROMPT_FILE_MAP
- `backend/api/routes/chat.py` — 改用 load_prompt + 注入 consult_context + knowledge_context 占位空串
- `backend/main.py` — lifespan 改从 prompt_service 导入合并后的 CODE_DEFAULTS / PROMPT_FILE_MAP
- `admin-spa/src/types/prompt.ts` — PROMPT_KEY_LABELS / PROMPT_KEY_DESCRIPTIONS 补 b2b_system / b2b_few_shot

### 新增测试
- `backend/tests/integration/test_prompt_admin_b2b.py` — b2b 提示词 CRUD + 双写
- `backend/tests/snapshot/test_markdown_constraint.py` — B2B/consult 回复不含 markdown 符号

---

## Task 1: 在 prompts_b2b.py 加 Markdown 约束和占位符

**Files:**
- Modify: `backend/agents/conversation/prompts_b2b.py`

- [ ] **Step 1: 读取当前 prompts_b2b.py 确认结构**

Run: `Read backend/agents/conversation/prompts_b2b.py`
Expected: 文件包含 `B2B_SYSTEM_PROMPT`（约 60 行）和 `B2B_FEW_SHOT_EXAMPLES`（约 40 行列表），无 CODE_DEFAULTS / PROMPT_FILE_MAP。

- [ ] **Step 2: 在 B2B_SYSTEM_PROMPT 中加 consult_context 和 knowledge_context 占位符**

定位到 `B2B_SYSTEM_PROMPT` 字符串中现有的 `## 咨询历史（来自咨询模块，仅供参考）\n{consult_context}` 段落 — 如果当前没有，则在 `## 已收集信息\n{slots_summary}` 之后追加两段。

使用 Edit 工具，old_string 为：
```
## 已收集信息
{slots_summary}

## RIASEC 参考
```
new_string 为：
```
## 已收集信息
{slots_summary}

## 咨询历史（来自咨询模块，仅供参考）
{consult_context}

## 知识库参考（学校官方信息，必须来自此处）
{knowledge_context}

## RIASEC 参考
```

如果原文件已有 `## 咨询历史` 段落，则跳过追加 consult_context 段落（仅加 knowledge_context 段落）。

- [ ] **Step 3: 在 B2B_SYSTEM_PROMPT 末尾加 Markdown 约束小节**

使用 Edit 工具，old_string 为：
```
## 注意事项
- 每次回复 2-5 句话
- 一次只问一个问题
- 学生焦虑时先共情再继续
- 不要在对话初期就推荐专业——先充分了解学生
- 如果你不知道我校某个具体数据，诚实说明，不要编造
"""
```
new_string 为：
```
## 注意事项
- 每次回复 2-5 句话
- 一次只问一个问题
- 学生焦虑时先共情再继续
- 不要在对话初期就推荐专业——先充分了解学生
- 如果你不知道我校某个具体数据，诚实说明，不要编造
- 学校官方信息（院系设置、专业介绍、招生政策）必须来自「## 知识库参考」段；不在检索结果中的具体数据，诚实说"我校暂未公开"或"我不确定"，不要编造
- 个性化建议（兴趣/价值观匹配）可自由发挥，不依赖检索结果

## 输出格式（必须严格遵守）
- 使用纯文本，禁止使用任何 markdown 语法（** ## - ` 等）
- 强调关键词时用中文引号「」，如「人工智能专业」
- 列举时用中文数字（一、二、三、 或 1. 2. 3.）
- 禁止输出 markdown 表格
- 数字直接写，不加任何修饰符号
"""
```

- [ ] **Step 4: 在文件末尾加 CODE_DEFAULTS 和 PROMPT_FILE_MAP**

在 `B2B_FEW_SHOT_EXAMPLES = [...]` 列表结束后追加：

```python


# 代码默认值映射表，供 prompt_service 回退使用
import json as _json
CODE_DEFAULTS = {
    "b2b_system": B2B_SYSTEM_PROMPT,
    "b2b_few_shot": _json.dumps(B2B_FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2),
}

# prompt_key → (代码文件相对路径, 常量名) 映射，供 prompt_sync_service 使用
PROMPT_FILE_MAP = {
    "b2b_system": ("agents/conversation/prompts_b2b.py", "B2B_SYSTEM_PROMPT"),
    "b2b_few_shot": ("agents/conversation/prompts_b2b.py", "B2B_FEW_SHOT_EXAMPLES"),
}
```

注：`B2B_FEW_SHOT_EXAMPLES` 是 Python list，存入 CODE_DEFAULTS 时需 JSON 序列化为字符串（与 prompt_template.content 类型一致）。

- [ ] **Step 5: 验证文件语法正确**

Run: `cd backend; python -c "from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT, CODE_DEFAULTS, PROMPT_FILE_MAP; print(len(CODE_DEFAULTS), list(PROMPT_FILE_MAP.keys()))"`
Expected: 输出 `2 ['b2b_system', 'b2b_few_shot']`，无 SyntaxError。

- [ ] **Step 6: 验证占位符存在**

Run: `cd backend; python -c "from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT as p; assert '{consult_context}' in p; assert '{knowledge_context}' in p; print('placeholders OK')"`
Expected: 输出 `placeholders OK`

- [ ] **Step 7: Commit**

```bash
git add backend/agents/conversation/prompts_b2b.py
git commit -m "feat(prompts): add markdown constraint + consult/knowledge placeholders + CODE_DEFAULTS to B2B prompt"
```

---

## Task 2: 在 prompt_service.py 合并 consult + b2b 的 CODE_DEFAULTS / PROMPT_FILE_MAP

**Files:**
- Modify: `backend/services/prompt_service.py`

- [ ] **Step 1: 读取当前 prompt_service.py**

Run: `Read backend/services/prompt_service.py`
Expected: 从 `agents.conversation.prompts_consult` 单源导入 CODE_DEFAULTS（第 8 行）。

- [ ] **Step 2: 替换 import 语句为合并两个模块**

使用 Edit 工具，old_string 为：
```python
from agents.conversation.prompts_consult import CODE_DEFAULTS
```
new_string 为：
```python
from agents.conversation.prompts_consult import CODE_DEFAULTS as _CONSULT_DEFAULTS
from agents.conversation.prompts_consult import PROMPT_FILE_MAP as _CONSULT_MAP
from agents.conversation.prompts_b2b import CODE_DEFAULTS as _B2B_DEFAULTS
from agents.conversation.prompts_b2b import PROMPT_FILE_MAP as _B2B_MAP

# 合并 consult + b2b 两个模块的映射表，单一来源供 prompt_admin / prompt_sync_service / lifespan 使用
CODE_DEFAULTS = {**_CONSULT_DEFAULTS, **_B2B_DEFAULTS}
PROMPT_FILE_MAP = {**_CONSULT_MAP, **_B2B_MAP}
```

- [ ] **Step 3: 验证合并后包含 5 个 key**

Run: `cd backend; python -c "from services.prompt_service import CODE_DEFAULTS, PROMPT_FILE_MAP; print(sorted(CODE_DEFAULTS.keys())); print(sorted(PROMPT_FILE_MAP.keys()))"`
Expected: 输出两行，均含 `['b2b_few_shot', 'b2b_system', 'consult_degraded', 'consult_intent', 'consult_system']`（5 项）。

- [ ] **Step 4: 验证 load_prompt 能回退 b2b_system**

Run: `cd backend; python -c "import asyncio; from services.prompt_service import load_prompt; r = asyncio.run(load_prompt('b2b_system', 'scnu')); print('consult_context' in r, 'knowledge_context' in r, len(r) > 100)"`
Expected: 输出 `True True True`

- [ ] **Step 5: Commit**

```bash
git add backend/services/prompt_service.py
git commit -m "refactor(prompt_service): merge consult + b2b CODE_DEFAULTS and PROMPT_FILE_MAP"
```

---

## Task 3: prompt_admin.py 改从 prompt_service 导入合并后的 CODE_DEFAULTS

**Files:**
- Modify: `backend/api/routes/prompt_admin.py`

- [ ] **Step 1: 读取当前 prompt_admin.py 第 20 行附近**

Run: `Read backend/api/routes/prompt_admin.py` (offset 18, limit 5)
Expected: 第 21 行为 `from agents.conversation.prompts_consult import CODE_DEFAULTS`

- [ ] **Step 2: 替换 import 语句**

使用 Edit 工具，old_string 为：
```python
from agents.conversation.prompts_consult import CODE_DEFAULTS
```
new_string 为：
```python
from services.prompt_service import CODE_DEFAULTS
```

- [ ] **Step 3: 验证导入无循环依赖**

Run: `cd backend; python -c "from api.routes.prompt_admin import router; print('import OK', len(router.routes))"`
Expected: 输出 `import OK 4`（4 个路由：list/get/update/sync），无 ImportError。

- [ ] **Step 4: Commit**

```bash
git add backend/api/routes/prompt_admin.py
git commit -m "refactor(prompt_admin): import CODE_DEFAULTS from prompt_service (merged source)"
```

---

## Task 4: prompt_sync_service.py 改从 prompt_service 导入合并后的 PROMPT_FILE_MAP

**Files:**
- Modify: `backend/services/prompt_sync_service.py`

- [ ] **Step 1: 读取当前 prompt_sync_service.py 第 1-20 行**

Run: `Read backend/services/prompt_sync_service.py` (limit 20)
Expected: 第 11 行 `from agents.conversation.prompts_consult import PROMPT_FILE_MAP as CONSULT_MAP`，第 14 行 `PROMPT_FILE_MAP = dict(CONSULT_MAP)`。

- [ ] **Step 2: 替换 import 和合并逻辑**

使用 Edit 工具，old_string 为：
```python
from agents.conversation.prompts_consult import PROMPT_FILE_MAP as CONSULT_MAP

_logger = logging.getLogger(__name__)

# 合并 consult 与 b2b 的映射（b2b 暂用同一 map，后续扩展）
PROMPT_FILE_MAP = dict(CONSULT_MAP)
```
new_string 为：
```python
from services.prompt_service import PROMPT_FILE_MAP

_logger = logging.getLogger(__name__)
```

- [ ] **Step 3: 验证 PROMPT_FILE_MAP 含 5 个 key**

Run: `cd backend; python -c "from services.prompt_sync_service import PROMPT_FILE_MAP; print(sorted(PROMPT_FILE_MAP.keys()))"`
Expected: 输出 `['b2b_few_shot', 'b2b_system', 'consult_degraded', 'consult_intent', 'consult_system']`

- [ ] **Step 4: 验证 sync_to_code_with_retry 对 b2b_system 可调用**

Run: `cd backend; python -c "from services.prompt_sync_service import sync_to_code_with_retry, PROMPT_FILE_MAP; assert 'b2b_system' in PROMPT_FILE_MAP; print('b2b_system syncable')"`
Expected: 输出 `b2b_system syncable`

- [ ] **Step 5: Commit**

```bash
git add backend/services/prompt_sync_service.py
git commit -m "refactor(prompt_sync): import merged PROMPT_FILE_MAP from prompt_service"
```

---

## Task 5: main.py lifespan 改从 prompt_service 导入合并后的映射

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 读取当前 main.py 第 180-200 行**

Run: `Read backend/main.py` (offset 178, limit 22)
Expected: 第 182 行 `from agents.conversation.prompts_consult import CODE_DEFAULTS, PROMPT_FILE_MAP`，第 187 行 `from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT`，第 188 行 `if "{consult_context}" not in B2B_SYSTEM_PROMPT:`。

- [ ] **Step 2: 替换 import 和校验逻辑**

使用 Edit 工具，old_string 为：
```python
    # 咨询模块启动一致性检查：验证 prompt 占位符与代码常量同步
    try:
        from agents.conversation.prompts_consult import CODE_DEFAULTS, PROMPT_FILE_MAP
        missing_keys = set(CODE_DEFAULTS.keys()) - set(PROMPT_FILE_MAP.keys())
        if missing_keys:
            logger.warning(f"PROMPT_FILE_MAP missing keys: {missing_keys}")
        # 验证 B2B prompt 含 consult_context 占位符
        from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT
        if "{consult_context}" not in B2B_SYSTEM_PROMPT:
            logger.warning("B2B_SYSTEM_PROMPT missing {consult_context} placeholder")
        else:
            logger.info("Consult module consistency check passed")
    except Exception as e:
        logger.warning(f"Consult module consistency check failed: {e}")
```
new_string 为：
```python
    # 提示词启动一致性检查：CODE_DEFAULTS 与 PROMPT_FILE_MAP 一致 + 关键占位符存在
    try:
        from services.prompt_service import CODE_DEFAULTS, PROMPT_FILE_MAP
        missing_keys = set(CODE_DEFAULTS.keys()) - set(PROMPT_FILE_MAP.keys())
        if missing_keys:
            logger.warning(f"PROMPT_FILE_MAP missing keys: {missing_keys}")
        # 验证 B2B prompt 含 consult_context 和 knowledge_context 占位符
        from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT
        for placeholder in ("{consult_context}", "{knowledge_context}"):
            if placeholder not in B2B_SYSTEM_PROMPT:
                logger.warning(f"B2B_SYSTEM_PROMPT missing {placeholder} placeholder")
        else:
            logger.info(
                "Prompt consistency check passed: %d keys, B2B placeholders OK",
                len(CODE_DEFAULTS),
            )
    except Exception as e:
        logger.warning(f"Prompt consistency check failed: {e}")
```

- [ ] **Step 3: 验证启动校验通过**

Run: `cd backend; python -c "import logging; logging.basicConfig(level=logging.INFO); from services.prompt_service import CODE_DEFAULTS, PROMPT_FILE_MAP; from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT; missing = set(CODE_DEFAULTS.keys()) - set(PROMPT_FILE_MAP.keys()); assert not missing; assert '{consult_context}' in B2B_SYSTEM_PROMPT; assert '{knowledge_context}' in B2B_SYSTEM_PROMPT; print('check passes', len(CODE_DEFAULTS), 'keys')"`
Expected: 输出 `check passes 5 keys`

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "refactor(main): import merged CODE_DEFAULTS/PROMPT_FILE_MAP from prompt_service + check both B2B placeholders"
```

---

## Task 6: chat.py 改用 load_prompt + 注入 consult_context + knowledge_context 占位空串

**Files:**
- Modify: `backend/api/routes/chat.py`

- [ ] **Step 1: 读取 chat.py 第 1-20 行（import）和第 170-185 行（system_content 构建）**

Run: `Read backend/api/routes/chat.py` (limit 20) 和 `Read backend/api/routes/chat.py` (offset 168, limit 18)
Expected:
- 第 10 行：`from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT`
- 第 178-185 行：`elif uni_name:` 分支内 `system_content = B2B_SYSTEM_PROMPT.format(university_name=..., university_short=..., stage=..., slots_summary=...)`（无 consult_context / knowledge_context 参数）

- [ ] **Step 2: 替换 B2B_SYSTEM_PROMPT import 为 load_prompt + build_consult_context**

使用 Edit 工具，old_string 为：
```python
from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT
```
new_string 为：
```python
from services.prompt_service import load_prompt
from services.consult_context_service import build_consult_context
```

- [ ] **Step 3: 替换 B2B_SYSTEM_PROMPT.format 调用为 load_prompt + consult_context + knowledge_context 注入**

定位 `elif uni_name:` 分支（约第 178 行），使用 Edit 工具，old_string 为：
```python
            elif uni_name:
                system_content = B2B_SYSTEM_PROMPT.format(
                    university_name=uni_name,
                    university_short=uni_short or uni_name,
                    stage=current_stage.value,
                    slots_summary=slots_text,
                )
```
new_string 为：
```python
            elif uni_name:
                # 动态加载 B2B 提示词（DB 优先，代码默认值回退）
                b2b_template = await load_prompt("b2b_system", tenant_slug)
                # 注入咨询历史上下文（仅注册用户）
                consult_context = ""
                user_id_state = state_data.get("user_id")
                if user_id_state:
                    try:
                        consult_context = await build_consult_context(
                            user_id=user_id_state,
                            tenant_slug=tenant_slug,
                        )
                    except Exception as e:
                        _logger.warning(f"build_consult_context failed: {e}")
                        consult_context = ""
                # knowledge_context 占位（Plan 2 替换为真实 RAG 检索结果）
                knowledge_context = ""
                system_content = b2b_template.format(
                    university_name=uni_name,
                    university_short=uni_short or uni_name,
                    stage=current_stage.value,
                    slots_summary=slots_text,
                    consult_context=consult_context,
                    knowledge_context=knowledge_context,
                )
```

- [ ] **Step 4: 在文件顶部加 _logger（若不存在）**

使用 Grep 检查 `chat.py` 是否已有 `_logger = logging.getLogger(__name__)`。若无，则在 import 块之后、`router = APIRouter()` 之前追加：

```python
import logging

_logger = logging.getLogger(__name__)
```

- [ ] **Step 5: 验证 chat.py 语法正确**

Run: `cd backend; python -c "from api.routes.chat import router; print('chat import OK', len(router.routes))"`
Expected: 输出 `chat import OK 5`（5 个路由：PATCH /profile + WS /session/{id} + POST /session + GET /session/{id} + DELETE /session/{id}），无 SyntaxError / ImportError。

- [ ] **Step 6: 验证 B2B_SYSTEM_PROMPT 硬编码 import 已移除**

Run: `cd backend; python -c "import ast; src = open('api/routes/chat.py', encoding='utf-8').read(); assert 'from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT' not in src, 'hardcoded import still present'; print('hardcoded import removed')"`
Expected: 输出 `hardcoded import removed`

- [ ] **Step 7: Commit**

```bash
git add backend/api/routes/chat.py
git commit -m "feat(chat): load B2B prompt via load_prompt + inject consult_context + knowledge_context placeholder"
```

---

## Task 7: 前端 prompt.ts 补 b2b_system / b2b_few_shot 标签

**Files:**
- Modify: `admin-spa/src/types/prompt.ts`

- [ ] **Step 1: 读取当前 prompt.ts 第 31-42 行**

Run: `Read admin-spa/src/types/prompt.ts` (offset 29, limit 14)
Expected: `PROMPT_KEY_LABELS` 含 3 项（consult_system / consult_intent / consult_degraded），`PROMPT_KEY_DESCRIPTIONS` 含 3 项。

- [ ] **Step 2: 在 PROMPT_KEY_LABELS 中追加 b2b 两项**

使用 Edit 工具，old_string 为：
```ts
export const PROMPT_KEY_LABELS: Record<string, string> = {
  consult_system: '咨询模块 - 系统提示词',
  consult_intent: '咨询模块 - 意图抽取',
  consult_degraded: '咨询模块 - 降级重生成',
}
```
new_string 为：
```ts
export const PROMPT_KEY_LABELS: Record<string, string> = {
  consult_system: '咨询模块 - 系统提示词',
  consult_intent: '咨询模块 - 意图抽取',
  consult_degraded: '咨询模块 - 降级重生成',
  b2b_system: '推荐模块 - 系统提示词',
  b2b_few_shot: '推荐模块 - Few-shot 示例',
}
```

- [ ] **Step 3: 在 PROMPT_KEY_DESCRIPTIONS 中追加 b2b 两项**

使用 Edit 工具，old_string 为：
```ts
export const PROMPT_KEY_DESCRIPTIONS: Record<string, string> = {
  consult_system: '咨询模块主回答的 system prompt。控制回答风格、数据引用规则、输出格式。',
  consult_intent: '从用户消息抽取意图（intent_type/majors/province/year）的 prompt。返回 JSON。',
  consult_degraded: '校验失败后的降级重生成 prompt。强制逐条陈述数据表，禁止归纳。',
}
```
new_string 为：
```ts
export const PROMPT_KEY_DESCRIPTIONS: Record<string, string> = {
  consult_system: '咨询模块主回答的 system prompt。控制回答风格、数据引用规则、输出格式。',
  consult_intent: '从用户消息抽取意图（intent_type/majors/province/year）的 prompt。返回 JSON。',
  consult_degraded: '校验失败后的降级重生成 prompt。强制逐条陈述数据表，禁止归纳。',
  b2b_system: '推荐模块主回答的 system prompt。控制对话风格、阶段引导、数据引用规则、输出格式。',
  b2b_few_shot: '推荐模块 Few-shot 示例（JSON 数组）。用于 LLM in-context learning，控制不同类型学生的回复风格。',
}
```

- [ ] **Step 4: 验证 TypeScript 编译通过**

Run: `cd admin-spa; npx tsc -b --noEmit`
Expected: 0 errors，无 `Property 'b2b_system' does not exist` 类报错。

- [ ] **Step 5: Commit**

```bash
git add admin-spa/src/types/prompt.ts
git commit -m "feat(admin-spa): add b2b_system and b2b_few_shot labels to prompt management UI"
```

---

## Task 8: 集成测试 — b2b 提示词 CRUD + 双写

**Files:**
- Test: `backend/tests/integration/test_prompt_admin_b2b.py`

- [ ] **Step 1: 读取现有 consult 提示词集成测试作为模板**

Run: `Glob backend/tests/integration/test_prompt*.py`
Expected: 找到 `test_prompt_admin.py` 或类似文件。

- [ ] **Step 2: 写测试文件**

使用 Write 工具创建 `backend/tests/integration/test_prompt_admin_b2b.py`：

```python
"""B2B 提示词管理集成测试 — CRUD + 双写。

测试契约：
- GET /admin/prompts 应返回 5 个 key（含 b2b_system / b2b_few_shot）
- GET /admin/prompts/b2b_system 应返回 code_default 非空
- PUT /admin/prompts/b2b_system 应创建新版本 + 触发代码双写
- load_prompt('b2b_system') 应返回含 consult_context/knowledge_context 占位符的内容
"""
import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_list_prompts_includes_b2b_keys(authenticated_client: AsyncClient):
    """GET /admin/prompts 应包含 b2b_system 和 b2b_few_shot。"""
    resp = await authenticated_client.get("/api/v1/admin/prompts")
    assert resp.status_code == 200
    keys = {p["prompt_key"] for p in resp.json()["prompts"]}
    assert "b2b_system" in keys
    assert "b2b_few_shot" in keys
    assert len(keys) == 5  # 3 consult + 2 b2b


@pytest.mark.asyncio
async def test_get_b2b_system_detail(authenticated_client: AsyncClient):
    """GET /admin/prompts/b2b_system 应返回非空 code_default。"""
    resp = await authenticated_client.get("/api/v1/admin/prompts/b2b_system")
    assert resp.status_code == 200
    body = resp.json()
    assert body["prompt_key"] == "b2b_system"
    assert body["code_default"]
    assert "{consult_context}" in body["code_default"]
    assert "{knowledge_context}" in body["code_default"]


@pytest.mark.asyncio
async def test_update_b2b_system_creates_new_version(authenticated_client: AsyncClient):
    """PUT /admin/prompts/b2b_system 应创建新版本且 is_active=True。"""
    new_content = "测试用 B2B prompt {university_name} {stage} {slots_summary} {consult_context} {knowledge_context}"
    resp = await authenticated_client.put(
        "/api/v1/admin/prompts/b2b_system",
        json={"content": new_content},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["prompt_key"] == "b2b_system"
    assert body["version"] >= 1
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_load_prompt_b2b_system_falls_back_to_code_default():
    """load_prompt('b2b_system') 应回退到代码默认值（含两个占位符）。"""
    from services.prompt_service import load_prompt
    content = await load_prompt("b2b_system", "scnu")
    assert content
    assert "{consult_context}" in content
    assert "{knowledge_context}" in content
```

- [ ] **Step 3: 确认测试夹具 authenticated_client 存在**

Run: `Grep backend/tests/integration/conftest.py "authenticated_client"`
Expected: 找到 fixture 定义。若无，参考现有 `test_prompt_admin.py` 的 fixture 使用方式调整测试。

- [ ] **Step 4: 运行测试验证失败（占位符缺失或 import 错误）**

Run: `cd backend; python -m pytest tests/integration/test_prompt_admin_b2b.py -v --tb=short`
Expected: 测试通过（因为 Task 1-6 已实现）。如果失败，检查 import 路径或 fixture 名。

- [ ] **Step 5: Commit**

```bash
git add backend/tests/integration/test_prompt_admin_b2b.py
git commit -m "test(prompt_admin): add integration tests for b2b_system and b2b_few_shot management"
```

---

## Task 9: 快照测试 — B2B/consult 回复不含 markdown 符号

**Files:**
- Test: `backend/tests/snapshot/test_markdown_constraint.py`

- [ ] **Step 1: 创建快照测试目录（若不存在）**

Run: `cd backend; if (-not (Test-Path tests/snapshot)) { New-Item -ItemType Directory -Path tests/snapshot }`
Expected: 目录存在或已创建。

- [ ] **Step 2: 写快照测试文件**

使用 Write 工具创建 `backend/tests/snapshot/test_markdown_constraint.py`：

```python
"""Markdown 约束快照测试 — 验证 B2B 和 consult 提示词均强制纯文本输出。

测试契约：
- B2B_SYSTEM_PROMPT 含「禁止使用任何 markdown 语法」字样
- CONSULT_SYSTEM_PROMPT 含「禁止使用任何 markdown 语法」字样
- 两个 prompt 均含「## 输出格式（必须严格遵守）」小节标题
- 两个 prompt 均含「中文引号「」」指引
- 两个 prompt 均含「禁止输出 markdown 表格」
"""
import re
from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT
from agents.conversation.prompts_consult import CONSULT_SYSTEM_PROMPT


def test_b2b_prompt_has_markdown_constraint():
    """B2B prompt 应含完整 markdown 约束小节。"""
    assert "## 输出格式（必须严格遵守）" in B2B_SYSTEM_PROMPT
    assert "禁止使用任何 markdown 语法" in B2B_SYSTEM_PROMPT
    assert "中文引号「」" in B2B_SYSTEM_PROMPT
    assert "禁止输出 markdown 表格" in B2B_SYSTEM_PROMPT


def test_consult_prompt_has_markdown_constraint():
    """Consult prompt 应含完整 markdown 约束小节。"""
    assert "## 输出格式（必须严格遵守）" in CONSULT_SYSTEM_PROMPT
    assert "禁止使用任何 markdown 语法" in CONSULT_SYSTEM_PROMPT
    assert "中文引号「」" in CONSULT_SYSTEM_PROMPT
    assert "禁止输出 markdown 表格" in CONSULT_SYSTEM_PROMPT


def test_b2b_prompt_no_markdown_in_output_guidance():
    """B2B prompt 的输出格式小节自身不应使用 markdown 符号（元一致性）。"""
    # 提取输出格式小节内容
    match = re.search(
        r"## 输出格式（必须严格遵守）\n(.*?)(?=\n## |\Z)",
        B2B_SYSTEM_PROMPT,
        re.DOTALL,
    )
    assert match, "输出格式小节不存在"
    section = match.group(1)
    # 小节内的指引行可以用 - 列举（这是 prompt 文本，不是 LLM 输出），但不应有 ** 加粗
    assert "**" not in section, f"输出格式小节内含 ** 加粗: {section}"
```

- [ ] **Step 3: 运行快照测试**

Run: `cd backend; python -m pytest tests/snapshot/test_markdown_constraint.py -v`
Expected: 3 个测试全部 PASS。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/snapshot/test_markdown_constraint.py
git commit -m "test(snapshot): verify markdown constraint in B2B and consult prompts"
```

---

## Task 10: 端到端验证 — 启动后端 + 前端，确认 5 个 key 可见

- [ ] **Step 1: 重启后端服务**

在已有 backend 终端（terminal_id: 6）按 Ctrl+C 停止 uvicorn，然后重新运行：
Run: `cd backend; uvicorn main:app --host 127.0.0.1 --port 8000 --reload`
Expected: 启动日志含 `Prompt consistency check passed: 5 keys, B2B placeholders OK`，无 `PROMPT_FILE_MAP missing keys` 警告。

- [ ] **Step 2: 重启前端服务**

在已有 mini-app 或 admin-spa 终端重启 dev server。admin-spa 需启动：
Run: `cd admin-spa; npm run dev -- --port 3001`
Expected: 编译无 TS 错误。

- [ ] **Step 3: 浏览器验证 AgentSettingsPage**

打开 `http://localhost:3001?tenant=scnu`，登录 `admin/admin123`，进入「智能体设置」页 →「提示词模板」Tab。
Expected: 列表显示 5 个条目：
- 咨询模块 - 系统提示词
- 咨询模块 - 意图抽取
- 咨询模块 - 降级重生成
- 推荐模块 - 系统提示词
- 推荐模块 - Few-shot 示例

- [ ] **Step 4: 验证 b2b_system 详情页可编辑**

点击「推荐模块 - 系统提示词」，查看详情。
Expected:
- code_default 非空
- 内容含 `{consult_context}` 和 `{knowledge_context}` 占位符
- 内容含「## 输出格式（必须严格遵守）」小节
- 可编辑保存

- [ ] **Step 5: Commit 验证记录（无代码变更，跳过 commit）**

记录验证结果到 session memory：
- 5 个 key 全部可见 ✓
- b2b_system 详情含两个占位符 ✓
- b2b_system 含 Markdown 约束小节 ✓
- 编辑保存功能正常 ✓

---

## Self-Review 检查

**Spec 覆盖：**
- 章节 4.1.1 prompts_b2b.py 改造 → Task 1 ✓
- 章节 4.1.2 prompt_service / prompt_admin / prompt_sync_service 合并 → Task 2, 3, 4 ✓
- 章节 4.1.3 chat.py 改造 → Task 6 ✓
- 章节 4.2 前端改造 → Task 7 ✓
- 章节 4.3 lifespan 启动校验 → Task 5 ✓
- 章节 4.4 B2B Markdown 约束 → Task 1 Step 3 ✓
- 章节 6 测试策略 → Task 8 (集成) + Task 9 (快照) ✓
- 章节 7 验收 #1, #2, #3, #5(回归), #10 → Task 10 ✓

**Placeholder 扫描：** 无 TBD/TODO，所有步骤含完整代码。

**Type 一致性：**
- `CODE_DEFAULTS` 在 Task 1/2/3/5 中名称一致
- `PROMPT_FILE_MAP` 在 Task 1/2/4/5 中名称一致
- `load_prompt("b2b_system", tenant_slug)` 在 Task 6 中调用，签名与 prompt_service 一致
- `build_consult_context(user_id=..., tenant_slug=...)` 在 Task 6 中调用，需确认 consult_context_service.py 的实际签名

**风险点：**
- Task 6 Step 3 的 `build_consult_context` 调用签名需与 `backend/services/consult_context_service.py` 实际签名对齐 — 实施时先 Read 该文件确认。
- Task 8 的 `authenticated_client` fixture 需与 conftest.py 实际定义对齐 — 实施时先 Grep 确认。
