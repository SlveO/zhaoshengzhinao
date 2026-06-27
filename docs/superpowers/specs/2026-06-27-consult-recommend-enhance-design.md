# 咨询-推荐双模块检索与提示词治理增强

> 设计日期：2026-06-27
> 状态：已确认，待实施
> 范围：提示词管理补全 + 双模块 Markdown 约束 + 意图提取重构 + 推荐模块 RAG 接入
> 前置：`docs/superpowers/specs/2026-06-27-consult-module-design.md`（咨询/推荐双模块拆分）

## 背景

在咨询/推荐双模块拆分完成后，扫描代码发现 4 个待修复问题：

1. **提示词管理范围与设计不符**：原设计（前序 spec 章节 A.1）规定 admin-spa 应可管理 5 个提示词（3 个 consult + 2 个 b2b），实际只实现了 3 个 consult。`B2B_SYSTEM_PROMPT` 在 `chat.py` 硬编码 import，未进 DB、未进 `load_prompt`、未进双写机制。
2. **双模块 Markdown 约束不对称**：`CONSULT_SYSTEM_PROMPT` 有「## 输出格式（必须严格遵守）」小节强制纯文本，`B2B_SYSTEM_PROMPT` 完全无输出格式约束，导致推荐对话可能输出 `**`/`##`/`-` 等 markdown 符号，与咨询模块风格不一致且前端渲染不可控。
3. **咨询 Phase 1 意图提取实现薄弱**：当前仅单次 LLM 抽取，无对话历史、无 slots 注入、无 tenant 专业词典约束、无规则兜底、无重试、JSON 解析容错弱。实际使用中导致 AI 咨询回答效果极差。
4. **推荐模块 RAG 检索缺失**：报考建议列表已有 `retrieve_candidates`（院校专业 metadata 检索），但推荐聊天 WebSocket 完全无 RAG，B2B LLM 凭空回答可能编造学校数据。设计文档章节 4.4 对比表标注"推荐模块数据引用=自由引用"是设计漏洞。

## 核心决策清单

| # | 决策点 | 选定方案 |
|---|---|---|
| 1 | B2B Markdown 约束严格度 | 严格纯文本，与 consult 对齐（禁任何 markdown 语法，强调用「」中文引号，列举用中文数字） |
| 2 | 提示词管理范围 | 合并 consult + b2b 的 CODE_DEFAULTS，5 个 key 全部纳入 admin-spa 在线管理 |
| 3 | 意图提取改造力度 | 参考企业知识库问答架构，"规则前置 + LLM 增强 + 融合校验"三阶段管道 |
| 4 | 推荐模块 RAG 覆盖范围 | 两个环节都加：推荐聊天 WebSocket + 报考建议列表 |
| 5 | 推荐聊天 RAG 延迟控制 | top_k=3，跳过意图抽取，目标 <300ms |
| 6 | 实施顺序 | 阶段 1（提示词+Markdown）→ 阶段 2（推荐 RAG）→ 阶段 3（意图提取），3 个独立 plan，一次性交付 |
| 7 | 共享检索服务 | 不抽取通用 recommend_retrieval_service（避免重构 retrieve_candidates 的调用方），两处独立实现 |

---

## 章节 1：方案总览

| 子项目 | 目标 | 改动范围 |
|---|---|---|
| A. 提示词管理补全 | `b2b_system` / `b2b_few_shot` 纳入 admin-spa 在线管理 + 双写 | prompts_b2b.py、prompt_admin.py、prompt_service.py、prompt_sync_service.py、chat.py；前端 prompt.ts |
| B. 双模块 Markdown 约束 | B2B 加严格纯文本小节，与 consult 风格对齐 | prompts_b2b.py |
| C. Phase 1 意图提取重构 | 规则+LLM 双层，支持多轮+slots+专业词典+融合校验 | consult.py、prompts_consult.py、新增 consult_intent_service.py |
| D. 推荐模块 RAG 双环节接入 | 推荐聊天 WebSocket + 报考建议列表都接入 RAG | chat.py、recommendation_service.py、新增 recommend_retrieval_service.py |

---

## 章节 2：意图提取重构（参考企业知识库问答架构）

### 2.1 设计灵感

- Dify 的 Query Rewriting 节点
- LangChain Multi-Query Retriever
- Coze 的"问题理解"节点
- 企业知识库问答的"问题归一化 + 实体识别 + 意图分类"三段式

### 2.2 核心思想

把单次 LLM 抽取升级为 **"规则前置 + LLM 增强 + 融合校验"** 三阶段管道。

### 2.3 处理流程

```
输入：user_content + history(最近 4 轮 user/assistant 消息) + slots(省/选科/分/位次) + tenant专业词典

[阶段 A] 规则前置（同步、零成本）
  - 显式数字提取：年份(20xx)、分数(3位)、位次(4-6位)
  - 关键词意图判定：
    "分数/位次/录取/多少分/最低分/投档" → data_query
    "政策/章程/选科要求/培养方案/转专业" → policy_query
    "介绍/课程/就业/怎么样/学什么" → major_intro
  - 专业词典正向匹配：扫描 user_content 中已收录专业名（含简称别名映射）
  ↓
[阶段 B] LLM 增强（temperature=0，含上下文+词典+slots）
  - 任务1：Query Rewriting — 把多轮指代消解为独立查询
           （"那个专业呢" → "人工智能专业 2024 年录取位次"）
  - 任务2：结构化抽取 — intent_type / majors / province / year / need_admission_data
  - Prompt 中明确：词典中的专业名优先；province/year 缺省从 slots 取
  ↓
[阶段 C] 融合校验
  - majors = 词典匹配 ∪ LLM 抽取（去重 + 词典标准化）
  - province/year/score_query 优先 LLM，缺失回退规则，再缺失回退 slots
  - need_admission_data = (intent_type=data_query) AND (用户提到分数/位次 OR majors 非空)
    — 不再纯靠 LLM
  - LLM 失败 → 用阶段 A 规则结果兜底，不直接降级 chitchat
  - JSON 解析失败 → 最多重试 1 次（提示词追加"上次输出无法解析，请严格输出 JSON"）
  ↓
[阶段 D] 检索路由
  - data_query + majors 非空 → SQL + RAG
  - data_query + majors 空 → 仅 RAG（用 rewritten query）
  - policy_query / major_intro → 仅 RAG
  - chitchat → 跳过检索
```

### 2.4 Intent 数据结构

```python
@dataclass
class Intent:
    intent_type: str  # "data_query" | "policy_query" | "major_intro" | "chitchat"
    majors: list[str]  # 标准化专业名（已通过词典归一）
    province: str  # 默认从 slots 取
    year: int | None
    score_query: int | None
    rank_query: int | None
    need_admission_data: bool
    rewritten_query: str  # 消解指代后的独立查询，供 RAG 使用
```

### 2.5 新增文件

`backend/services/consult_intent_service.py`：
- `extract_intent(user_content, history, slots, tenant_majors) -> Intent`
- `Intent` dataclass
- 内部封装规则前置 + LLM 调用 + 融合逻辑
- 失败兜底：返回 Intent(intent_type=chitchat, majors=[], ...) 而非抛异常

### 2.6 改造点

- `backend/api/routes/consult.py` Phase 1 替换为 `intent = await extract_intent(...)`
- `backend/agents/conversation/prompts_consult.py` `INTENT_EXTRACTION_PROMPT` 升级，新增 `{history}` `{slots_summary}` `{tenant_majors}` 三个占位符
- tenant 专业词典加载：从 `admission_data.major_name` 去重提取，启动时缓存到内存，每 10 分钟刷新一次（lru_cache + TTL）

### 2.7 预期效果

| 问题类型 | 当前表现 | 重构后 |
|---|---|---|
| 多轮"那个专业呢" | 识别为 chitchat | 通过 history 消解指代 |
| "我这个分能上吗" | score_query 丢失 | slots 注入兜底 |
| "AI 专业分数" | majors=["AI"]，SQL 查不到 | 词典标准化为"人工智能" |
| LLM 偶发失败 | 整链降级 chitchat | 规则兜底，保留 majors |
| "录取分多少"但 LLM 标 need_admission_data=false | 不查 SQL | 规则强制 need_admission_data=true |

---

## 章节 3：推荐模块 RAG 双环节接入

### 3.1 新增共享检索服务

新文件：`backend/services/recommend_retrieval_service.py`

```python
async def retrieve_for_chat(
    user_content: str,
    tenant_slug: str,
    user_slots: dict,
    top_k: int = 3,
) -> list[dict]:
    """推荐聊天用 — 轻量检索。
    
    直接用 user_content + slots 上下文做向量检索，
    返回 top_k 相关片段（学校介绍/专业/政策）。
    不走意图抽取，保持低延迟（<300ms）。
    
    返回结构与 consult 模块 sources 一致：
    [{text, source_title, source_url, score}, ...]
    """

async def retrieve_for_recommendations(
    profile: dict,
    tenant_slug: str,
    existing_candidates: list[dict],
) -> list[dict]:
    """报考建议列表用 — 增强检索。
    
    在现有 retrieve_candidates（院校专业 metadata）基础上，
    追加文本型 RAG（学校介绍/招生政策），用于丰富推荐理由。
    """
```

### 3.2 推荐聊天接入（chat.py）

在 WebSocket 消息处理循环中，LLM 调用前插入：
```python
# 新增：RAG 检索
slots_snapshot = acc.export_snapshot()
rag_sources = await retrieve_for_chat(
    user_content, tenant_slug, slots_snapshot, top_k=3
)
knowledge_context = format_rag_context(rag_sources)  # 格式化为 ## 知识库参考 小节

# B2B_SYSTEM_PROMPT 新增 {knowledge_context} 占位符
system_content = await load_prompt("b2b_system", tenant_slug).format(
    university_name=uni_name,
    university_short=uni_short,
    stage=current_stage.value,
    slots_summary=slots_text,
    consult_context=consult_context,  # 已有
    knowledge_context=knowledge_context,  # 新增
)
```

延迟控制：top_k=3 + 跳过意图抽取，目标 <300ms。

### 3.3 推荐聊天 RAG 数据引用规则（写入 B2B prompt）

- 学校官方信息（院系设置、专业介绍、招生政策）必须来自 `## 知识库参考`
- 不在检索结果中的具体数据 → 诚实说"我校暂未公开 / 我不确定"
- 个性化建议（兴趣/价值观匹配）可自由发挥

### 3.4 报考建议列表增强（recommendation_service.py）

保留现有 `retrieve_candidates`（院校专业 metadata），追加：
```python
# 新增：文本型 RAG 检索学校/专业介绍
text_sources = await retrieve_for_recommendations(
    profile, tenant_slug, candidates
)
# 注入 RANKING_PROMPT 的 {industry_data} 之后，新增 {school_context} 占位符
```

### 3.5 共享检索服务设计原则

- 不重构 `retrieve_candidates` 现有调用方（避免连锁影响）
- 两处独立调用 ChromaDB，但通过 `recommend_retrieval_service` 统一封装格式化逻辑
- `format_rag_context(sources) -> str` 公共函数，输出 `## 知识库参考\n1. {text}\n2. {text}` 格式

---

## 章节 4：提示词管理补全 + B2B Markdown 约束

### 4.1 后端改造

#### 4.1.1 prompts_b2b.py 改造

在 `B2B_SYSTEM_PROMPT` 加：
- `## 输出格式（必须严格遵守）` 小节（与 consult 对齐：纯文本、禁 markdown、强调用「」、列举用中文数字）
- `{knowledge_context}` 占位符（章节 3.2 用）
- `{consult_context}` 占位符（已有，保留）

文件末尾新增：
```python
CODE_DEFAULTS = {
    "b2b_system": B2B_SYSTEM_PROMPT,
    "b2b_few_shot": json.dumps(B2B_FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2),
}

PROMPT_FILE_MAP = {
    "b2b_system": ("agents/conversation/prompts_b2b.py", "B2B_SYSTEM_PROMPT"),
    "b2b_few_shot": ("agents/conversation/prompts_b2b.py", "B2B_FEW_SHOT_EXAMPLES"),
}
```

#### 4.1.2 prompt_service.py / prompt_admin.py / prompt_sync_service.py 改造

现有从 `prompts_consult.CODE_DEFAULTS` 单源导入 → 改为合并两个模块：

```python
# prompt_service.py
from agents.conversation.prompts_consult import CODE_DEFAULTS as _CONSULT_DEFAULTS
from agents.conversation.prompts_b2b import CODE_DEFAULTS as _B2B_DEFAULTS
CODE_DEFAULTS = {**_CONSULT_DEFAULTS, **_B2B_DEFAULTS}

from agents.conversation.prompts_consult import PROMPT_FILE_MAP as _CONSULT_MAP
from agents.conversation.prompts_b2b import PROMPT_FILE_MAP as _B2B_MAP
PROMPT_FILE_MAP = {**_CONSULT_MAP, **_B2B_MAP}
```

`prompt_admin.py`、`prompt_sync_service.py` 同步改为从 `prompt_service` 导入合并后的 `CODE_DEFAULTS` / `PROMPT_FILE_MAP`。

#### 4.1.3 chat.py 改造

```python
# 旧：from agents.conversation.prompts_b2b import B2B_SYSTEM_PROMPT
# 新：
from services.prompt_service import load_prompt

# 使用处：
system_template = await load_prompt("b2b_system", tenant_slug)
system_content = system_template.format(
    university_name=uni_name,
    university_short=uni_short or uni_name,
    stage=current_stage.value,
    slots_summary=slots_text,
    consult_context=consult_context,
    knowledge_context=knowledge_context,
)
```

### 4.2 前端改造

`admin-spa/src/types/prompt.ts` `PROMPT_KEY_LABELS` / `PROMPT_KEY_DESCRIPTIONS` 补两项：
```ts
b2b_system: '推荐模块 - 系统提示词',
b2b_few_shot: '推荐模块 - Few-shot 示例',
// descriptions:
b2b_system: '推荐模块主回答的 system prompt。控制对话风格、阶段引导、数据引用规则、输出格式。',
b2b_few_shot: '推荐模块 Few-shot 示例（JSON 数组）。用于 LLM in-context learning，控制不同类型学生的回复风格。',
```

`AgentSettingsPage.tsx` 无需改 — 已通过 `listPrompts()` 动态拉取，自动展示 5 个 key。

### 4.3 Lifespan 启动校验

`PROMPT_FILE_MAP` 合并后，启动校验自动覆盖 5 个 key（已实现于 `main.py` lifespan）。

### 4.4 B2B_SYSTEM_PROMPT 输出格式小节内容

```
## 输出格式（必须严格遵守）
- 使用纯文本，禁止使用任何 markdown 语法（** ## - ` 等）
- 强调关键词时用中文引号「」，如「人工智能专业」
- 列举时用中文数字（一、二、三、 或 1. 2. 3.）
- 禁止输出 markdown 表格
- 数字直接写，不加任何修饰符号
```

---

## 章节 5：实施顺序与依赖

```
阶段 1（独立、低风险）：A 提示词管理补全 + B Markdown 约束
  └─ 改 prompts_b2b.py / prompt_service.py / prompt_admin.py / prompt_sync_service.py / chat.py / prompt.ts
  └─ 不影响现有功能，可独立验证
  └─ 必须最先完成：阶段 2 依赖 {knowledge_context} 占位符

阶段 2（独立、中风险）：D 推荐模块 RAG
  └─ 新增 recommend_retrieval_service.py
  └─ 改 chat.py（注入 knowledge_context）+ recommendation_service.py
  └─ 依赖阶段 1 的 {knowledge_context} 占位符

阶段 3（核心、中风险）：C 意图提取重构
  └─ 新增 consult_intent_service.py
  └─ 改 consult.py + prompts_consult.py
  └─ 需要测试用例覆盖（多轮、指代、空 majors 等场景）
  └─ 与阶段 1/2 解耦，独立测试
```

3 个阶段对应 3 个独立 plan 文档，顺序执行，一次性交付。

---

## 章节 6：测试策略

| 模块 | 测试类型 | 用例 |
|---|---|---|
| 意图提取 | 单测 | 多轮指代、slots 兜底、词典匹配、LLM 失败降级、JSON 解析失败重试 |
| 推荐聊天 RAG | 集成 | WebSocket 消息含 RAG 来源、无检索结果时优雅降级、延迟 <500ms |
| 报考建议列表 | 集成 | 推荐理由含 school_context、不影响现有 candidates 数量 |
| 提示词管理 | 集成 | 5 个 key CRUD、b2b 保存触发双写、load_prompt 回退代码默认 |
| Markdown 约束 | 快照 | B2B/consult 回复不含 `**` `##` `-` 等符号 |
| 启动校验 | 集成 | lifespan 检测 5 个 key 的 PROMPT_FILE_MAP ↔ CODE_DEFAULTS 一致 |

测试规范遵循项目 CLAUDE.md：实现与测试分属不同 sub-agent，AAA 模式，LLM 测试需 mock/benchmark/snapshot 层。

---

## 章节 7：验收标准

| # | 验收项 | 验证方法 |
|---|---|---|
| 1 | admin-spa 提示词管理页显示 5 个 key | 打开 AgentSettingsPage → 提示词模板 Tab，应见 5 项 |
| 2 | b2b_system 保存后触发代码双写 | PUT /admin/prompts/b2b_system → 检查 prompts_b2b.py 已更新 |
| 3 | B2B 回复不含 markdown 符号 | 推荐聊天实测，正则 `[\*#\-` + \|]` 不命中 |
| 4 | 咨询回复不含 markdown 符号 | 咨询聊天实测（回归） |
| 5 | 意图提取支持多轮指代 | 第二轮"那个专业呢"能识别为人工智能 |
| 6 | 意图提取 slots 兜底 | "我这个分能上吗"能注入 score_query |
| 7 | 意图提取词典标准化 | "AI 专业"能归一化为"人工智能" |
| 8 | 推荐聊天 RAG 注入 | WebSocket 回复中可引用学校官方信息 |
| 9 | 报考建议列表含 school_context | RANKING_PROMPT 注入学校介绍文本 |
| 10 | lifespan 启动校验通过 | 启动日志无 PROMPT_FILE_MAP 不一致警告 |

---

## 章节 8：风险与降级

| 风险 | 影响 | 降级方案 |
|---|---|---|
| tenant 专业词典为空（新租户未导入数据） | 词典匹配失效 | 退化为纯 LLM 抽取，等同改造前 |
| ChromaDB 检索失败 | 推荐聊天无 RAG | 返回空 knowledge_context，B2B prompt 提示"暂无官方信息参考" |
| 意图提取 LLM 超时 | 咨询链路阻塞 | 3s 超时，降级为规则结果，继续后续流程 |
| B2B prompt 双写失败 | 代码常量未更新 | 已有 6 层保障机制（前序 spec 章节 A.4），DB 已更新 |
| b2b_few_shot JSON 格式被改坏 | Few-shot 失效 | load_prompt 后 JSON 解析失败 → 跳过 few-shot，不影响主流程 |

---

## 附录 A：文件变更清单

### 新增文件
- `backend/services/consult_intent_service.py` — 意图提取服务
- `backend/services/recommend_retrieval_service.py` — 推荐模块 RAG 服务

### 修改文件
- `backend/agents/conversation/prompts_b2b.py` — 加 Markdown 约束 + knowledge_context 占位符 + CODE_DEFAULTS / PROMPT_FILE_MAP
- `backend/agents/conversation/prompts_consult.py` — INTENT_EXTRACTION_PROMPT 加 history/slots_summary/tenant_majors 占位符
- `backend/services/prompt_service.py` — 合并 consult + b2b 的 CODE_DEFAULTS / PROMPT_FILE_MAP
- `backend/api/routes/prompt_admin.py` — 从 prompt_service 导入合并后的 CODE_DEFAULTS
- `backend/services/prompt_sync_service.py` — 从 prompt_service 导入合并后的 PROMPT_FILE_MAP
- `backend/api/routes/chat.py` — 改用 load_prompt("b2b_system") + 注入 RAG knowledge_context
- `backend/api/routes/consult.py` — Phase 1 改用 consult_intent_service.extract_intent
- `backend/services/recommendation_service.py` — 注入 school_context 到 RANKING_PROMPT
- `admin-spa/src/types/prompt.ts` — PROMPT_KEY_LABELS / PROMPT_KEY_DESCRIPTIONS 补 b2b 项

### 新增测试
- `backend/tests/unit/test_consult_intent_service.py`
- `backend/tests/integration/test_recommend_retrieval_service.py`
- `backend/tests/integration/test_prompt_admin_b2b.py`
- `backend/tests/snapshot/test_markdown_constraint.py`

---

## 附录 B：与前序 spec 的关系

本 spec 是 `2026-06-27-consult-module-design.md` 的增量增强，不修改前序 spec 的任何决策。涉及前序 spec 的内容时，本 spec 仅追加（如 B2B prompt 加占位符、加约束小节），不替换。

前序 spec 章节 4.4 对比表中"推荐模块数据引用=自由引用"一项，本 spec 章节 3.3 明确修正为"学校官方信息必须来自 RAG 检索结果，个性化建议可自由发挥"。
