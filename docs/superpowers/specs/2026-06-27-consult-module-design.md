# 咨询模块独立化与推荐模块上下文增强设计

> 设计日期：2026-06-27
> 状态：已确认，待实施
> 范围：mini-app 咨询/推荐双模块拆分 + 双层检索 + 后置校验 + 提示词在线编辑

## 背景

当前 mini-app 对话咨询 AI 存在以下问题：
1. RAG 流程缺少意图理解，所有问题统一检索，准确性低
2. AI 用较低位次专业的数据拼接用户咨询的专业名称回复，数据错误
3. AI 回复偏引导式反问，未优先完整回答用户问题
4. 咨询与个性化推荐混杂在同一对话中，职责不清
5. AI 回复带 markdown 符号（`**`/`##`）未渲染

本设计将对话系统拆分为「咨询模块」与「推荐模块」两个独立功能：
- **咨询模块**：客观严谨回答招生数据问题，最大程度确保信息无误
- **推荐模块**：分析理解用户情感进行引导，达到营销目的，并读取咨询会话记录增强上下文

## 核心决策清单

| # | 决策点 | 选定方案 |
|---|---|---|
| 1 | 模块拆分形态 | 方案 B：咨询聊天 + 推荐列表（推荐聊天降级为次级页面） |
| 2 | 会话隔离 | session_id 前缀（`sess_consult_xxx` / `sess_xxx`），不加 schema 字段 |
| 3 | 检索策略 | 双层检索：意图抽取 → SQL 精确查询 + RAG 文本检索 |
| 4 | 意图抽取与 RAG 关系 | 顺序执行（先意图后 RAG），按 intent_type 动态构建 RAG query |
| 5 | 后置校验 | mismatch/fabricated/wrong_major 检测，重生成上限 1 次 |
| 6 | 降级处理 | 重生成仍失败时，数据注入上下文重生成 + 黄色警示气泡 |
| 7 | 提示词风格 | 客观严谨，禁止共情语/反问/markdown |
| 8 | 提示词管理 | DB 表 + 代码常量双写，集成到现有 AgentSettingsPage |
| 9 | Markdown 渲染 | 方案 A：仅 Prompt 约束禁止 markdown，前端零改动 |
| 10 | 双写可靠性 | 6 层保障：重试+队列+启动校验+健康检查+乐观锁+告警 |
| 11 | tabBar 设计 | 3 项：咨询/推荐/我的 |
| 12 | 登录态管理 | 全局 store（stores/auth.ts） |
| 13 | 推荐模块上下文 | 读取最近活跃咨询会话的摘要+消息+intent_majors 注入 B2B prompt |

---

## 章节 1：整体架构

### 1.1 模块拆分

```
mini-app/src/pages/
├── consult/           # 【新增】咨询模块 — 客观严谨 Q&A
│   └── index.vue
├── chat/              # 【保留改造】推荐聊天 — 情感引导营销
│   └── index.vue
└── recommendations/   # 【保留】推荐列表 — 10条卡片
    └── index.vue
```

### 1.2 后端路由

| 路由 | 模块 | 用途 | 状态 |
|---|---|---|---|
| `POST /api/v1/miniapp/enter` | 共享 | 创建/恢复会话 | 保留（扩展 module_type） |
| `POST /api/v1/consult/messages` | 咨询 | 双层检索+校验重生成 | 新增 |
| `POST /api/v1/chat/messages` | 推荐 | B2B 引导式对话 | 保留 |
| `POST /api/v1/recommendations` | 推荐 | 10条列表 | 保留 |
| `GET/PUT/POST /api/v1/admin/prompts/...` | 管理 | 提示词编辑 | 新增 |
| `GET /api/v1/health/prompts` | 管理 | 同步健康检查 | 新增 |

### 1.3 前端导航

底部 Tab（3 个）：
- 咨询 → /pages/consult/index
- 推荐 → /pages/recommendations/index
- 我的 → /pages/profile/index

推荐聊天页 `/pages/chat/index` 不再作为主入口，改为从「推荐 Tab」顶部按钮"和 AI 聊聊"进入（次级页面）。

### 1.4 共享与隔离边界

| 共享 | 隔离 |
|---|---|
| 会话创建/恢复（enter） | 提示词 |
| 用户基础信息读取（users 表） | 检索策略（双层 vs 纯 RAG） |
| 历史消息存储（chat_messages） | 后置校验逻辑 |
| 画像桥（仅推荐模块触发） | SSE 事件结构 |
| 咨询摘要服务（共享） | 意图理解 prompt |

---

## 章节 2：双层检索与意图理解

### 2.1 流程总览

```
用户消息
  ↓
[Step 1] 意图理解（LLM-1，结构化抽取，temp=0）
  → {intent_type, majors[], province, year, score_query, rank_query, need_admission_data}
  ↓
[Step 2a] 结构化查询（SQL → admission_data 表，与 RAG 并行）
  → 精确数据：专业×年份×省份的 min_score/min_rank/subject_requirements
  ↓
[Step 2b] RAG 检索（向量 → ChromaDB，基于 intent 结果构建 query）
  → 文本片段：招生章程/专业介绍/政策说明
  ↓
[Step 3] 上下文组装（结构化表 + 文本片段）
  ↓
[Step 4] 主回答生成（LLM-2，强约束 prompt，temp=0.3）
  ↓
[Step 5] 后置校验 → 不通过则重生成（章节 3）
```

### 2.2 Step 1：意图理解（LLM-1）

模型：DeepSeek，`temperature=0`（求确定性）

Prompt（INTENT_EXTRACTION_PROMPT）：
```
你是高考咨询意图分析助手。从用户消息中抽取以下结构化字段，严格按 JSON 输出，无匹配则置 null：
{
  "intent_type": "data_query" | "policy_query" | "major_intro" | "chitchat",
  "majors": ["专业名1", "专业名2"],
  "province": "广东",
  "year": 2024,
  "score_query": 585,
  "rank_query": 32000,
  "need_admission_data": true
}
```

输出处理：
- JSON 解析失败 → 降级为 `{intent_type:"chitchat", need_admission_data:false}`
- `intent_type=data_query` 且 `need_admission_data=true` → 走双层
- `intent_type=policy_query/major_intro` → 仅走 RAG
- `intent_type=chitchat` → 跳过检索

前端 SSE 事件：`intent_extracted` 下发结构化摘要（如"已识别：人工智能专业 / 2024年 / 广东"）。

### 2.3 Step 2a：结构化查询

新文件：`backend/services/consult_retrieval_service.py`

```python
async def query_admission_data(
    majors: list[str],
    province: str,
    year: int | None,
    tenant_college_id: uuid.UUID,
) -> list[dict]:
    """精确查询 admission_data 表。"""
```

查询逻辑：
1. 优先按 `(major_name IN majors) AND province AND year` 查询
2. 若 `year` 为空，取该专业最新 3 年数据
3. 专业名模糊匹配：`major_name ILIKE '%{m}%'`
4. 限定 `college_id = scnu.id`（多租户隔离）

空结果处理：返回空列表，prompt 中告知"该专业无录取数据"。

### 2.4 Step 2b：RAG 检索

保留：`search_similar(query, 5, tenant_slug)` ChromaDB 检索

**RAG Query 构建规则**（基于 intent_type 与 majors 动态构建）：

| intent_type | majors | RAG Query 构建规则 | 示例 |
|---|---|---|---|
| `data_query` | 非空 | `"{专业名} 录取 分数 位次 {省份}"` | `"人工智能 录取 分数 位次 广东"` |
| `data_query` | 空 | 原始 user_content | `"2024 年位次多少能上华师"` |
| `policy_query` | 非空 | `"{专业名} 招生章程 选科要求 培养方案"` | `"人工智能 招生章程 选科要求 培养方案"` |
| `policy_query` | 空 | `"{原始user_content} 招生政策"` | `"转专业政策 招生政策"` |
| `major_intro` | 非空 | `"{专业名} 专业介绍 课程 就业前景"` | `"人工智能 专业介绍 课程 就业前景"` |
| `major_intro` | 空 | `"{原始user_content} 专业介绍"` | `"计算机类专业 专业介绍"` |
| `chitchat` | 任意 | 跳过 RAG | — |

多专业场景：`majors=[人工智能, 软件工程]` → query=`"人工智能 软件工程 录取 分数 位次 广东"`

返回：保留 sources 结构（text/source_title/source_url/score）

### 2.5 Step 3：上下文组装

System Prompt 结构：
```
[CONSULT_SYSTEM_PROMPT]
├── 角色定义：华南师范大学招生信息助手
├── 强约束规则（详见章节 4）
├── 用户基础信息：省份/选科/分数/位次（来自 users 表）
├── ## 录取数据（结构化，硬证据）        ← Step 2a 结果（Markdown 表格）
│   | 专业 | 年份 | 省份 | 批次 | 最低分 | 最低位次 | 选科要求 |
└── ## 知识库检索结果（参考）            ← Step 2b 结果
```

录取数据表用 Markdown 表格注入，明确标注"以下为数据库精确数据，回复中引用的位次/分数必须与此表一致"。

### 2.6 执行顺序与并行

- **顺序**：意图抽取 → RAG 查询构建
- **并行**：admission_data SQL 查询 ∥ RAG 向量检索（asyncio.gather）
- **总延迟预估**：3.3-5.3s（一次通过）

---

## 章节 3：后置校验重生成机制

### 3.1 触发条件

仅当 Step 2a 返回了结构化录取数据时触发（`admission_rows` 非空）。

### 3.2 校验内容

新文件：`backend/services/consult_validator.py`

```python
@dataclass
class ValidationIssue:
    major_in_reply: str
    metric: str  # "min_score" | "min_rank"
    value_in_reply: int
    matched_db_row: dict | None
    issue_type: str  # "mismatch" | "fabricated" | "wrong_major"
```

校验规则：
1. 正则提取回复中所有「专业名 + 数字」组合
2. 对每个组合，在 admission_rows 中找匹配专业
3. 比对 min_score / min_rank

| 场景 | 判定 | 处理 |
|---|---|---|
| 回复数字匹配 DB | pass | 不触发重生成 |
| 回复数字与 DB 不一致 | mismatch | 触发重生成 |
| 回复中专业在 DB 中不存在 | fabricated | 触发重生成 |
| 回复数字是其他专业的（专业错配） | wrong_major | 触发重生成 |

### 3.3 重生成流程

```
[LLM-2 主回答] → reply_v1
  ↓
[validate_response(reply_v1, admission_rows)]
  ↓
  通过 → 返回
  不通过 → 组装纠错 prompt（DEGRADED_REGENERATION_PROMPT）→ LLM-2 再调用 → reply_v2
    ↓
    [validate_response(reply_v2, ...)]
    通过 → 返回 v2
    仍不通过 → 降级处理
```

### 3.4 重生成次数限制

**硬上限 1 次**。

### 3.5 降级处理

重生成仍失败时：
1. **直接将检索到的录取数据注入上下文重新生成**（数据驱动回复）
2. 前端追加黄色警示气泡：「⚠️ 本次回答中的部分数据未经系统校验通过，建议核对官方来源」

降级重生成 Prompt（DEGRADED_REGENERATION_PROMPT）：
```
你的回复中存在数据错误，已失败 1 次重生成。现在请直接基于数据表逐条陈述，不要做任何归纳或推理。

## 强制输出格式
1. 先列出数据表中所有相关行（按年份倒序）
2. 再用 1-2 句话回答用户原始问题
3. 禁止出现数据表以外的任何数字

## 数据表
{admission_table}

## 用户原始问题
{user_content}
```

### 3.6 SSE 事件扩展

| 事件类型 | 触发时机 | 前端表现 |
|---|---|---|
| `validation_start` | 主回答完成后 | 不显示（静默校验） |
| `validation_passed` | 校验通过 | 不显示 |
| `regenerating` | 触发重生成 | "正在核对数据，优化回答..." |
| `validation_warning` | 重生成仍失败 | 追加黄色警示气泡 |
| `done` | 全部完成 | 同现有 |

校验阶段前端已显示的 reply_v1 不擦除，重生成时**原地替换**为 reply_v2（用相同 message_id）。

### 3.7 性能影响

| 场景 | 占比预估 | 额外延迟 | 额外 LLM 调用 |
|---|---|---|---|
| 一次通过 | ~70% | +50ms（正则校验） | 0 |
| 重生成通过 | ~25% | +2-3s | +1 |
| 降级警告 | ~5% | +2-3s | +1 |
| 平均 | 100% | +0.7s | +0.3 |

### 3.8 边界情况

| 情况 | 处理 |
|---|---|
| LLM-2 回复中无任何数字 | 跳过校验，直接返回 |
| admission_rows 有多专业多年份 | 全部纳入校验范围 |
| 回复中专业名是简称（"AI"代"人工智能"） | 维护简称映射表，校验前标准化 |
| 回复中位次是范围（"3-4 万位"） | 提取范围上下界，与 DB 值比对是否在范围内 |
| 回复引用了 RAG 片段中的数字 | RAG 片段中的数字不纳入校验，prompt 约束"录取数据以表格为准" |

---

## 章节 4：咨询提示词重写

### 4.1 新文件位置

`backend/agents/conversation/prompts_consult.py`（与 `prompts_b2b.py` 平级）

### 4.2 CONSULT_SYSTEM_PROMPT 完整内容

```python
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
```

### 4.3 占位符说明

| 占位符 | 来源 | 示例 |
|---|---|---|
| `{slots_summary}` | users 表 + session 快照 | `"省份: 广东, 选科: 物化生, 分数: 585, 位次: 32000"` |
| `{admission_table}` | Step 2a 结构化查询结果 | Markdown 表格 或 "（暂无相关录取数据）" |
| `{knowledge_context}` | Step 2b RAG 检索结果 | 同现有实现 |

### 4.4 与 B2B 提示词对比

| 维度 | B2B_SYSTEM_PROMPT（推荐模块） | CONSULT_SYSTEM_PROMPT（咨询模块） |
|---|---|---|
| 角色 | 招生顾问，有感情 | 信息助手，无感情 |
| 核心目标 | 帮学生找到适合专业 | 准确回答问题 |
| 提问策略 | 渐进式提问，每轮 1-2 问 | 禁止反问 |
| 共情 | 焦虑时先共情 | 禁止共情语 |
| 推荐专业 | 主动引导介绍 | 仅用户主动问才答 |
| 数据引用 | 自由引用 | 严格限定表格 |
| 长度 | 2-5 句 | 2-5 句 |
| 个性化 | RIASEC 兴趣挖掘 | 不分析兴趣 |

### 4.5 意图理解 Prompt

```python
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
```

### 4.6 降级重生成 Prompt

```python
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
```

---

## 补充章节 A：提示词在线编辑集成方案

### A.1 整合到现有 AgentSettingsPage

不新增 Tab，重构 `admin-spa/src/pages/AgentSettingsPage.tsx` 为多提示词编辑器：

```
左侧：提示词列表（5 项）
  ├── 咨询-系统提示词 (consult_system)
  ├── 咨询-意图抽取 (consult_intent)
  ├── 咨询-降级重生成 (consult_degraded)
  ├── 推荐-系统提示词 (b2b_system)
  └── 推荐-Few-shot 示例 (b2b_few_shot)

右侧：编辑区
  ├── 版本号 / 最后修改时间 / 最后修改人
  ├── textarea 编辑器
  ├── 占位符说明（如 {slots_summary} / {admission_table}）
  ├── [保存] [重置为代码默认值] 按钮
  └── 渲染预览（用示例数据填充占位符）
```

### A.2 新增表：`prompt_templates`

```python
class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_slug: Mapped[str] = mapped_column(String(50), default="scnu", index=True)
    prompt_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("tenant_slug", "prompt_key", "version"),)
```

### A.3 双写机制（DB 表 + 代码常量同步）

加载逻辑：
```python
async def load_prompt(prompt_key: str, tenant_slug: str = "scnu") -> str:
    """优先 DB，回退代码常量。"""
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
    return CODE_DEFAULTS[prompt_key]
```

保存逻辑（双写）：
```python
@router.put("/admin/prompts/{prompt_key}")
async def update_prompt(prompt_key, body, db, user=Depends(require_developer)):
    # 1. 写入 DB（新建一行，version+1，旧版本 is_active=false）
    await _upsert_prompt_to_db(db, prompt_key, body.content, user.id)
    await db.commit()
    # 2. 同步写入代码常量文件
    sync_result = await sync_to_code_with_retry(prompt_key, body.content)
    if not sync_result.success:
        await redis.lpush("prompt_sync_queue", json.dumps({...}))
    return {"version": new_version, "sync_status": ..., "warning": ...}
```

### A.4 6 层可靠性保障

| 保障层 | 触发条件 | 行为 | 阻塞用户 |
|---|---|---|---|
| 层 1：保存不抛错 | 同步失败 | DB 已保存，仅 warning | 否 |
| 层 2：失败重试 | 同步首次失败 | 3 次指数退避（1s/2s/4s） | 否 |
| 层 3：异步队列兜底 | 重试全失败 | 入 Redis 队列，5 分钟重试一次，最大 10 次 | 否 |
| 层 4：启动时一致性校验 | 服务启动 | 比对 DB 与代码常量，不一致告警 | 否 |
| 层 5：健康检查端点 | Admin 查看 | `/health/prompts` 显示队列与不一致 | N/A |
| 层 6：乐观锁防并发 | 并发编辑 | expected_version 检查，409 拒绝后写者 | 是（提示重试） |

### A.5 重置接口

```python
@router.post("/admin/prompts/{prompt_key}/reset")
async def reset_prompt(prompt_key: str, ...):
    """重置为代码常量：删除该 key 的所有 DB 记录。"""
```

### A.6 代码常量文件同步

```python
PROMPT_FILE_MAP = {
    "consult_system": "agents/conversation/prompts_consult.py",
    "consult_intent": "agents/conversation/prompts_consult.py",
    "consult_degraded": "agents/conversation/prompts_consult.py",
    "b2b_system": "agents/conversation/prompts_b2b.py",
    "b2b_few_shot": "agents/conversation/prompts_b2b.py",
}
CONST_NAME_MAP = {
    "consult_system": "CONSULT_SYSTEM_PROMPT",
    "consult_intent": "INTENT_EXTRACTION_PROMPT",
    "consult_degraded": "DEGRADED_REGENERATION_PROMPT",
    "b2b_system": "B2B_SYSTEM_PROMPT",
    "b2b_few_shot": "B2B_FEW_SHOT_EXAMPLES",
}

async def _sync_to_code_file(prompt_key: str, content: str):
    """用正则替换 .py 文件中的常量定义。"""
```

### A.7 健康检查端点

```python
@router.get("/health/prompts")
async def prompt_sync_health(db: AsyncSession = Depends(get_db)):
    queue_size = await redis.llen("prompt_sync_queue")
    inconsistencies = await check_db_code_consistency(db)
    return {
        "status": "healthy" if queue_size == 0 and not inconsistencies else "degraded",
        "pending_sync": queue_size,
        "inconsistencies": inconsistencies
    }
```

Admin-SPA 在 AgentSettingsPage 顶部展示同步状态。

### A.8 接口响应

```json
{
  "prompt_key": "consult_system",
  "version": 3,
  "sync_status": "synced" | "retrying" | "queued",
  "sync_attempts": 1,
  "warning": null | "代码常量同步失败，已入队重试"
}
```

前端根据 `sync_status` 展示：
- `synced`：绿色 toast「保存成功」
- `retrying`：黄色 toast「保存成功，代码同步重试中」
- `queued`：橙色 toast「DB 已保存，代码同步失败，已入队重试」

---

## 补充章节 B：Markdown 限制方案 A

### B.1 Prompt 约束（已在 CONSULT_SYSTEM_PROMPT 中）

```
## 输出格式（必须严格遵守）
- 使用纯文本，禁止使用任何 markdown 语法（** ## - ` 等）
- 强调关键词时用中文引号「」，如「人工智能专业」
- 列举时用中文数字（一、二、三、 或 1. 2. 3.）
- 禁止输出 markdown 表格，数据用自然语言表述
- 数字直接写，不加任何修饰符号
```

### B.2 推荐模块同步约束

在 `B2B_SYSTEM_PROMPT` 中追加同样条款。

### B.3 前端零改动

继续用 `<text>{{ message.content }}</text>`，依赖 prompt 约束输出纯文本。

---

## 章节 5：前端模块与导航

### 5.1 文件结构

```
mini-app/src/
├── pages/
│   ├── consult/           # 【新增】咨询模块
│   │   └── index.vue
│   ├── chat/              # 【保留改造】推荐聊天（次级页面）
│   │   └── index.vue
│   ├── recommendations/   # 【保留】推荐列表
│   │   └── index.vue
│   └── profile/           # 【保留】我的
│       └── index.vue
├── pages.json             # 【修改】tabBar 改 3 项
├── stores/
│   └── auth.ts            # 【新增】全局登录态
└── components/
    └── ChatBubble.vue     # 【新增】共享气泡组件
```

### 5.2 pages.json 修改

```json
{
  "tabBar": {
    "list": [
      {"pagePath": "pages/consult/index", "text": "咨询"},
      {"pagePath": "pages/recommendations/index", "text": "推荐"},
      {"pagePath": "pages/profile/index", "text": "我的"}
    ]
  }
}
```

### 5.3 ConsultPage 布局

复用现有 chat 页面的 UI 结构与 SSE 处理逻辑，关键差异：
1. 顶部 mode-banner：明确告知用户当前是「咨询模式」
2. 调用 `POST /api/v1/consult/messages`
3. SSE 事件处理：
   - `intent_extracted`：显示结构化摘要
   - `search_start`/`source`/`search_end`：保留检索进度展示
   - `token`：流式追加
   - `regenerating`：显示「正在核对数据，优化回答...」
   - `validation_warning`：追加黄色警示气泡
   - `done`：结束
4. 移除 entry overlay 与 LoginModal 逻辑（共享全局登录态）
5. 移除画像抽取相关 UI

### 5.4 ChatBubble 组件（共享）

```vue
<template>
  <view :class="['bubble', role]">
    <text class="content">{{ content }}</text>
    <view v-if="sources?.length" class="sources">
      <text v-for="(s, i) in sources" :key="i" class="source-tag">{{ s.source_title }}</text>
    </view>
    <view v-if="warning" class="warning">⚠️ {{ warning }}</view>
  </view>
</template>

<script setup>
defineProps<{
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{ source_title: string; source_url: string }>
  warning?: string
}>()
</script>
```

### 5.5 推荐聊天页降级

`pages/chat/index.vue` 保留现有实现，调整：
1. 移除 onLoad 中的 entry overlay 逻辑（与 consult 共享全局登录态）
2. 顶部加返回按钮（次级页面导航）

从 recommendations 页跳转：
```vue
<view class="header">
  <text class="title">个性化推荐</text>
  <button class="chat-entry" @click="navigateToChat">和 AI 聊聊</button>
</view>
```

### 5.6 全局登录态管理

```ts
// stores/auth.ts
const TOKEN_KEY = 'auth_token'

export function getValidToken(): string | null {
  return uni.getStorageSync(TOKEN_KEY) || null
}

export function requireAuth(redirectOnFail: string = '/pages/login/index'): string | null {
  const token = getValidToken()
  if (!token) {
    uni.reLaunch({ url: redirectOnFail })
    return null
  }
  return token
}
```

consult/index.vue 与 chat/index.vue 在 onLoad 调用 `requireAuth()`。

### 5.7 推荐模块顶部改造

```
┌────────────────────────────┐
│  个性化推荐         [和AI聊聊] │
├────────────────────────────┤
│  你的位次：32000             │
│  推荐状态：基于位次和意向      │
├────────────────────────────┤
│  推荐卡片 1                 │
│  推荐卡片 2                 │
│  ...                       │
└────────────────────────────┘
```

---

## 章节 6：后端路由与 API 设计

### 6.1 路由清单

新增路由：
| 方法 | 路径 | 鉴权 | 用途 |
|---|---|---|---|
| POST | `/api/v1/consult/messages` | JWT | 咨询 SSE 流 |
| GET | `/api/v1/admin/prompts` | developer | 列出所有提示词 |
| GET | `/api/v1/admin/prompts/{key}` | developer | 获取单个提示词 |
| PUT | `/api/v1/admin/prompts/{key}` | developer | 更新提示词（双写） |
| POST | `/api/v1/admin/prompts/{key}/reset` | developer | 重置为代码默认值 |
| GET | `/api/v1/admin/prompts/{key}/versions` | developer | 版本历史 |
| GET | `/api/v1/health/prompts` | developer | 同步健康检查 |

保留路由：`/api/v1/miniapp/enter`、`/api/v1/chat/messages`、`/api/v1/recommendations`、`/api/v1/auth/*`

### 6.2 咨询 SSE 接口

`POST /api/v1/consult/messages`

请求：
```json
{
  "session_id": "sess_consult_xxx",
  "tenant_slug": "scnu",
  "message": {"content": "人工智能专业 2024 年录取位次是多少？"}
}
```

响应：`text/event-stream`

SSE 事件序列：
```
event: thinking
data: {"status": "正在理解你的问题..."}

event: intent_extracted
data: {"intent_type": "data_query", "majors": ["人工智能"], "province": "广东", "year": 2024, "need_admission_data": true}

event: search_start
data: {"stage": "structured"}

event: search_end
data: {"admission_rows": 2, "rag_sources": 3}

event: source
data: {"index": 1, "title": "人工智能专业介绍", "url": "..."}

event: token
data: {"content": "人"}
...

event: validation_start
data: {}

event: validation_passed
data: {}

event: done
data: {"message_id": "msg_xxx", "session_id": "sess_consult_xxx"}
```

校验失败重生成：
```
event: regenerating
data: {"issues": [{"type": "mismatch", "major": "人工智能", "metric": "min_rank", "reply_value": 32000, "db_value": 45000}]}

event: token
data: {"content": "..."}

event: done
data: {"message_id": "msg_xxx", "regenerated": true}
```

降级：
```
event: validation_warning
data: {"message": "本次回答中的部分数据未经系统校验通过，请核对官方来源"}

event: done
data: {"message_id": "msg_xxx", "degraded": true}
```

### 6.3 提示词管理接口

`GET /api/v1/admin/prompts`：
```json
{
  "prompts": [
    {
      "prompt_key": "consult_system",
      "version": 2,
      "is_active": true,
      "updated_by": "dev_xxx",
      "updated_at": "2026-06-27T10:00:00Z",
      "content_preview": "你是华南师范大学招生信息助手..."
    }
  ]
}
```

`PUT /api/v1/admin/prompts/{key}`：
- 请求：`{"content": "...", "expected_version": 2}`
- 响应：`{"prompt_key": "...", "version": 3, "sync_status": "synced", "sync_attempts": 1, "warning": null}`

### 6.4 后端文件结构

```
backend/
├── api/routes/
│   ├── consult.py          # 【新增】咨询 SSE 路由
│   └── prompt_admin.py     # 【新增】提示词管理路由
├── services/
│   ├── consult_retrieval_service.py  # 【新增】结构化+RAG 检索
│   ├── consult_validator.py          # 【新增】后置校验
│   ├── prompt_service.py             # 【新增】提示词加载
│   ├── prompt_sync_service.py        # 【新增】代码常量同步
│   └── recommend_context_service.py  # 【新增】推荐读取咨询上下文
├── agents/conversation/
│   └── prompts_consult.py            # 【新增】咨询提示词常量
└── models/
    └── prompt_template.py            # 【新增】ORM 模型
```

### 6.5 中间件与依赖链

```python
@router.post("/messages")
async def send_consult_message(
    body: ConsultMessageRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user),
    tenant = Depends(resolve_tenant),
    module_gate = Depends(ModuleGate("consult")),
):
    ...
```

### 6.6 错误处理

| 场景 | HTTP 状态码 | 响应 |
|---|---|---|
| 未登录 | 401 | `{"detail": "Not authenticated"}` |
| 会话不存在 | 404 | `{"detail": "Session not found"}` |
| 租户未启用 consult 模块 | 403 | `{"detail": "Module disabled"}` |
| LLM 调用失败 | 200 (SSE) | `event: error data: {"message": "..."}` |
| 提示词 key 无效 | 400 | `{"detail": "Invalid prompt key"}` |
| 乐观锁版本冲突 | 409 | `{"detail": "Version conflict: expected X, got Y"}` |
| 代码同步失败 | 200 | 返回 `sync_status: "queued"`，不抛错 |

### 6.7 会话隔离机制

```python
CONSULT_SESSION_PREFIX = "sess_consult_"
RECOMMEND_SESSION_PREFIX = "sess_"

async def get_or_create_session(
    session_id: str | None,
    user_id: uuid.UUID,
    tenant_slug: str,
    module_type: str = "recommend",
) -> ConsultSession:
    prefix = CONSULT_SESSION_PREFIX if module_type == "consult" else RECOMMEND_SESSION_PREFIX
    if not session_id or not session_id.startswith(prefix):
        session_id = f"{prefix}{uuid.uuid4().hex[:16]}"
    ...
```

---

## 章节 7：数据流与状态依赖

### 7.1 咨询模块完整数据流

```
[1] 前端 consult/index.vue onLoad
    ↓ requireAuth()
    ↓ 读取 consult_session_id
    ↓ POST /api/v1/miniapp/enter {module_type: "consult"}
    ↓
[2] 后端创建/恢复咨询会话（前缀 sess_consult_）
    ↓ 从 users 表快照基础信息
    ↓ 返回 session_id + chat_history(最近20条)
    ↓
[3] 用户输入消息 → POST /api/v1/consult/messages
    ↓ SSE 连接
    ↓
[4] 后端预处理
    ↓ save_message → chat_messages 表
    ↓ 首条用户消息记录 consult_started_at
    ↓ event: thinking
    ↓
[5] LLM-1 意图抽取 (temp=0, JSON)
    ↓ INTENT_EXTRACTION_PROMPT
    ↓ event: intent_extracted
    ↓
[6] 基于 intent 构建 RAG query
    ↓ 并行执行（asyncio.gather）：
    ├─ [6a] admission_data SQL 查询（need_admission_data=true 时）
    └─ [6b] RAG 向量检索（chitchat 跳过）
    ↓ event: source × N
    ↓ event: search_end
    ↓
[7] 上下文组装
    ↓ slots_summary ← users 表（排除手机号）或 session 快照
    ↓ admission_table ← admission_rows Markdown 表格
    ↓ knowledge_context ← RAG top-5 片段
    ↓ history ← chat_messages 最近 10 条
    ↓ system_prompt ← load_prompt("consult_system").format(...)
    ↓
[8] LLM-2 主回答生成 (temp=0.3, 流式)
    ↓ event: token × N
    ↓ 累积 reply_v1
    ↓
[9] 后置校验（仅当 admission_rows 非空）
    ↓ event: validation_start
    ↓ validate_response(reply_v1, admission_rows)
    ↓
    ├─ 通过 → event: validation_passed
    │       ↓ save_message(role="assistant", content=reply_v1)
    │       ↓ event: done
    │
    └─ 不通过 → event: regenerating
        ↓ DEGRADED_REGENERATION_PROMPT
        ↓ LLM-2 第 2 次调用 → reply_v2
        ↓ event: token × N（前端原地替换）
        ↓ validate_response(reply_v2, ...)
        ↓
        ├─ 通过 → save_message(reply_v2)
        │       ↓ event: done {regenerated: true}
        │
        └─ 仍不通过 → event: validation_warning
            ↓ save_message(reply_v2, metadata={warning: true})
            ↓ event: done {degraded: true}
    ↓
[10] 异步任务（非阻塞）
    ↓ asyncio.create_task(maybe_generate_summary(session_id))
    ↓ 触发：user_count>=4 首次，之后每 2 轮
    ↓ 写入 consult_sessions.consult_summary
```

### 7.2 推荐模块数据流（修订：读取咨询上下文）

```
[1] 前端 chat/index.vue onLoad
    ↓ requireAuth()
    ↓ POST /api/v1/miniapp/enter {module_type: "recommend"}
    ↓
[2] 后端创建/恢复推荐会话
    ↓ 查找用户最近活跃的咨询会话（sess_consult_）
    ↓ 绑定 context_ref_session_id
    ↓ 返回 session_id
    ↓
[3] 用户输入 → POST /api/v1/chat/messages
    ↓
[4] 后端预处理（save_message）
    ↓
[5] 加载推荐上下文（新增）
    ↓ load_consult_context(recommend_session, db)
    ↓   → 咨询摘要 consult_summary
    ↓   → 咨询中提及的专业 intent_majors
    ↓   → 咨询最近 3 轮对话片段
    ↓
[6] RAG 检索（基于当前 user_content + mentioned_majors）
    ↓ RAG query = user_content + " " + mentioned_majors[0]（如有）
    ↓
[7] 上下文组装
    ↓ B2B_SYSTEM_PROMPT.format(
    ↓     slots_summary=...,
    ↓     knowledge_context=...,
    ↓     consult_context=load_consult_context()  ← 新增
    ↓ )
    ↓ + history(10) + [HumanMessage]
    ↓
[8] LLM-2 主回答（B2B 引导风格）
    ↓
[9] Profile Bridge（每 3 轮，保留）
    ↓ 画像抽取输入也包含 consult_context
    ↓
[10] 异步摘要（保留）
```

### 7.3 推荐模块读取咨询上下文方案

#### 数据模型扩展

```python
# consult_sessions 表新增字段
class ConsultSession(Base):
    ...
    context_ref_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    # 推荐会话创建时，写入用户最近活跃的咨询会话 ID
    # 咨询会话此字段为 None
```

#### 推荐会话创建逻辑

```python
async def get_or_create_session(user_id, tenant_slug, module_type, ...):
    if module_type == "recommend":
        # 查找用户最近活跃的咨询会话
        recent_consult = await db.execute(
            select(ConsultSession).where(
                ConsultSession.user_id == user_id,
                ConsultSession.tenant_slug == tenant_slug,
                ConsultSession.session_id.like("sess_consult_%"),
                ConsultSession.consult_started_at.isnot(None),
            ).order_by(ConsultSession.updated_at.desc()).limit(1)
        )
        recent_consult = recent_consult.scalar_one_or_none()
        session = ConsultSession(
            session_id=f"sess_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            context_ref_session_id=recent_consult.id if recent_consult else None,
            ...
        )
```

#### 加载咨询上下文

新文件：`backend/services/recommend_context_service.py`

```python
async def load_consult_context(
    recommend_session: ConsultSession,
    db: AsyncSession,
) -> str:
    """加载关联咨询会话的对话摘要，注入推荐模块 system prompt。"""
    if not recommend_session.context_ref_session_id:
        return ""
    
    consult_session = await db.get(ConsultSession, recommend_session.context_ref_session_id)
    summary = consult_session.consult_summary or ""
    
    # 读取咨询会话最近 6 条消息（3 轮）
    messages = await db.execute(
        select(ChatMessage).where(
            ChatMessage.session_id == consult_session.session_id
        ).order_by(ChatMessage.created_at.desc()).limit(6)
    )
    messages = list(reversed(messages.scalars().all()))
    
    # 提取咨询中提及的专业
    mentioned_majors = consult_session.intent_majors or []
    
    context = f"""## 学生近期咨询记录（来自咨询模块）
咨询摘要：{summary or '（暂无摘要）'}

近期咨询中提及的专业：{', '.join(mentioned_majors) if mentioned_majors else '无'}

近期对话片段（最近3轮）：
"""
    for msg in messages:
        role = "学生" if msg.role == "user" else "AI"
        context += f"{role}：{msg.content[:100]}\n"
    
    context += """
## 引导建议
- 可基于学生近期咨询的专业，主动推荐相似或相关专业
- 避免重复询问学生已在咨询中提供的信息（省份/选科/分数/位次）
- 可自然衔接：「你刚才了解了XX专业，我为你推荐几个相关方向...」
"""
    return context
```

#### B2B System Prompt 扩展

```python
B2B_SYSTEM_PROMPT = """...
## 学生近期咨询记录（来自咨询模块）
{consult_context}

## 引导规则
- 如果学生近期咨询中提及了具体专业，可在合适时机主动推荐相关方向
- 不要重复询问学生已在咨询中提供的基础信息
- 自然衔接咨询话题，避免突兀切换
"""
```

#### 边界情况

| 场景 | 处理 |
|---|---|
| 用户从未使用咨询模块 | `context_ref_session_id=None`，`consult_context=""`，推荐模块行为不变 |
| 咨询会话已过期 | 仍可读取（chat_messages 不随 session 过期删除） |
| 用户在咨询中无有效对话（<3 条消息） | 加载最近消息但摘要为空，prompt 中标注"暂无摘要" |
| 用户多次咨询会话 | 只取最近 1 个活跃会话 |
| 推荐模块引导推荐的专业与咨询提及专业重复 | 接受：自然衔接 |

#### 性能影响

| 项目 | 耗时 |
|---|---|
| 查询最近咨询会话 | 30ms（session 创建时一次） |
| 加载咨询上下文 | 50ms（每轮推荐对话前） |
| 推荐模块总延迟增量 | +50ms |

### 7.4 数据读取与写入对照

#### 咨询模块

| 操作 | 目标表 | 触发时机 |
|---|---|---|
| 读 | users（region/subjects/score/rank，排除 phone/username） | 每轮主回答前 |
| 读 | consult_sessions（fallback） | users 表读取失败时 |
| 读 | chat_messages（最近 10 条） | 每轮主回答前 |
| 读 | admission_data | need_admission_data=true |
| 读 | ChromaDB（top-5） | 每轮（与 SQL 并行，chitchat 跳过） |
| 读 | prompt_templates（consult_*） | 每轮 |
| 写 | chat_messages | 用户发送 + 主回答完成 |
| 写 | consult_sessions.consult_started_at | 首条用户消息 |
| 写 | consult_sessions.consult_summary | 异步触发 |
| 写 | prompt_templates | Admin 保存时 |
| 写 | prompts_consult.py 常量 | Admin 保存时（双写） |

#### 推荐模块（保留现有 + 新增）

| 操作 | 目标表 | 触发时机 |
|---|---|---|
| 读 | users / consult_sessions | 每轮 |
| 读 | chat_messages（最近 10 条） | 每轮 |
| 读 | ChromaDB | 每轮 |
| 读 | session_profiles | 每 3 轮（画像桥） |
| 读 | prompt_templates（b2b_system） | 每轮 |
| 读 | consult_sessions（context_ref 关联的咨询会话） | 每轮（新增） |
| 读 | chat_messages（咨询会话最近 6 条） | 每轮（新增） |
| 写 | chat_messages | 每轮 |
| 写 | session_profiles | 每 3 轮 |
| 写 | consult_sessions.intent_majors | 每轮（regex）+ 每 3 轮（LLM） |
| 写 | consult_sessions.consult_summary | 异步触发 |
| 写 | data/extracted_profiles/*.json | 每 3 轮 |

### 7.5 关键状态约束

1. **会话隔离**：咨询与推荐 session_id 前缀不同，chat_messages 自然隔离
2. **基础信息双源**：users 表为主，consult_sessions 快照为 fallback
3. **画像桥仅推荐模块**：咨询模块不触发 profile_bridge
4. **咨询摘要共享**：两模块都触发 consult_summary_service
5. **提示词独立**：consult_system vs b2b_system
6. **校验仅咨询模块**：推荐模块无 admission_data 查询，无后置校验
7. **推荐模块读取咨询上下文**：通过 context_ref_session_id 绑定

### 7.6 性能预算

| 阶段 | 耗时预估 |
|---|---|
| save_message | 30ms |
| 意图抽取 | 300-500ms |
| RAG 检索 + admission_data 查询（并行） | 100-200ms |
| 上下文组装 | 10ms |
| LLM-2 主回答（首 token） | 800-1200ms |
| LLM-2 流式输出 | 2-4s |
| 后置校验 | 30-50ms |
| 重生成（如有） | 2-3s |
| **总计（一次通过）** | **3.3-5.3s** |
| **总计（触发重生成）** | **5.3-8.3s** |

---

## 章节 8：迁移与回滚

### 8.1 数据库迁移

新增 Alembic migration：`backend/alembic/versions/XXX_add_consult_module.py`

```python
def upgrade():
    # 1. 新增 prompt_templates 表
    op.create_table(
        "prompt_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_slug", sa.String(50), nullable=False, server_default="scnu"),
        sa.Column("prompt_key", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.clock_timestamp()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_slug", "prompt_key", "version", name="uq_prompt_version"),
    )
    op.create_index("ix_prompt_tenant_key", "prompt_templates", ["tenant_slug", "prompt_key"])
    op.create_index("ix_prompt_active", "prompt_templates", ["is_active"])

    # 2. consult_sessions 新增 context_ref_session_id
    op.add_column("consult_sessions",
        sa.Column("context_ref_session_id", UUID(as_uuid=True), nullable=True))
    op.create_index("ix_consult_sessions_context_ref", "consult_sessions", ["context_ref_session_id"])

def downgrade():
    op.drop_index("ix_consult_sessions_context_ref", table_name="consult_sessions")
    op.drop_column("consult_sessions", "context_ref_session_id")
    op.drop_index("ix_prompt_active", table_name="prompt_templates")
    op.drop_index("ix_prompt_tenant_key", table_name="prompt_templates")
    op.drop_table("prompt_templates")
```

迁移原则：
- 线性化 revision 链（避免多 head 冲突）
- upgrade 与 downgrade 完整对称
- 不修改现有字段，仅新增列和表

### 8.2 现有数据兼容

| 现有数据 | 影响 | 处理 |
|---|---|---|
| `consult_sessions` 现有行 | `context_ref_session_id` 为 NULL | 无需处理 |
| `chat_messages` 现有数据 | 无字段变更 | 无需处理 |
| 现有推荐会话 `sess_xxx` | 兼容 | 前缀匹配 `sess_consult_` 才视为咨询会话 |
| `prompt_templates` 空表 | 首次加载 fallback 到代码常量 | `load_prompt()` 自动处理 |

### 8.3 部署阶段

#### 阶段 1：后端部署（不影响现有功能）

1. 执行 Alembic migration
2. 部署后端代码（新增文件 + 修改 miniapp.py / consult_service.py）
3. 现有路由 `/api/v1/chat/messages` 行为不变
4. 启动后 lifespan 执行 `check_prompt_consistency()`

**回滚**：执行 `alembic downgrade -1`，恢复后端代码。

#### 阶段 2：Admin-SPA 部署

1. 重构 `AgentSettingsPage.tsx` 为多提示词编辑器
2. 新增 prompts API 客户端

**回滚**：CF Pages 回滚到上一部署版本。

#### 阶段 3：Mini-app 部署

1. 新增 `pages/consult/index.vue`、`components/ChatBubble.vue`、`stores/auth.ts`
2. 修改 `pages.json`、`pages/chat/index.vue`、`pages/recommendations/index.vue`

**回滚**：CF Pages 回滚到上一部署版本。后端兼容（旧 mini-app 不调用 /consult/messages）。

### 8.4 灰度策略

```python
# backend/config.py
class Settings(BaseSettings):
    consult_module_enabled: bool = False  # 默认关闭
```

```python
@router.post("/messages")
async def send_consult_message(..., settings: Settings = Depends(get_settings)):
    if not settings.consult_module_enabled:
        raise HTTPException(403, "Consult module disabled")
    ...
```

mini-app 通过 `/api/v1/miniapp/config` 读取 flag，决定是否显示咨询 Tab。

### 8.5 回滚预案

| 故障场景 | 回滚操作 | 影响 |
|---|---|---|
| 咨询模块后端报错 | 关闭 `consult_module_enabled` flag | 咨询 Tab 隐藏，推荐模块继续工作 |
| 提示词编辑导致 LLM 输出异常 | Admin 调用 `/reset` 接口 | 立即生效，无需重启 |
| DB 迁移失败 | `alembic downgrade -1` | 数据库恢复迁移前状态 |
| 推荐模块读取咨询上下文异常 | `context_ref_session_id` 置 NULL | 推荐模块降级为无咨询上下文模式 |
| 双写代码同步队列堆积 | 处理队列或清空 | 仅影响下次部署前的代码一致性 |

### 8.6 验收测试清单

#### 后端

| 测试项 | 验收标准 |
|---|---|
| Alembic upgrade/downgrade | 双向执行成功 |
| `/api/v1/consult/messages` SSE | 事件序列完整，全流程通过 |
| 意图抽取准确性 | 5 类 intent_type 测试用例 ≥90% 正确分类 |
| admission_data 查询 | 专业名精确+模糊匹配，多专业多年份场景 |
| 后置校验 | mismatch/fabricated/wrong_major 三类触发重生成 |
| 降级处理 | 重生成仍失败时返回警示气泡 |
| `/api/v1/admin/prompts` CRUD | 5 个 prompt_key 全通过 |
| 双写机制 | DB + 代码文件同步，失败时入队重试 |
| 推荐模块读取咨询上下文 | context_ref 绑定正确，prompt 中 consult_context 非空 |
| 现有 `/api/v1/chat/messages` | 行为不变，回归测试通过 |

#### Admin-SPA

| 测试项 | 验收标准 |
|---|---|
| AgentSettingsPage 多提示词编辑 | 5 个提示词切换、编辑、保存、重置全通过 |
| 健康状态展示 | 队列数、不一致数正确显示 |
| 乐观锁 | 并发编辑返回 409 |

#### Mini-app

| 测试项 | 验收标准 |
|---|---|
| tabBar 3 项导航 | 咨询/推荐/我的 切换正常 |
| 全局登录态 | requireAuth 未登录跳转 login，登录后所有页共享 |
| 咨询页 SSE | 意图摘要+检索进度+流式回答+警示气泡正确渲染 |
| 咨询页消息流 | 用户消息+AI 回复正确存入 chat_messages |
| 推荐聊天入口 | recommendations 页"和 AI 聊聊"跳转 chat 页 |
| 推荐页读取咨询上下文 | 切换到推荐模块后 AI 自然衔接咨询话题 |
| Markdown 不渲染 | AI 回复中无 `**` `##` 等残留符号 |

#### 端到端

| 场景 | 验收标准 |
|---|---|
| 注册→咨询→推荐 | 全链路数据正确流转 |
| 咨询"人工智能 2024 位次" | 回复位次与 admission_data 表一致 |
| 校验失败场景 | 重生成后数据正确，或显示警示 |
| 切换设备 | session 跨设备恢复，基础信息从 users 表读取 |

### 8.7 风险与对策

| 风险 | 概率 | 影响 | 对策 |
|---|---|---|---|
| LLM 意图抽取 JSON 解析失败 | 中 | 跳过 SQL 查询，仅 RAG | 降级为 chitchat 处理，记录日志 |
| admission_data 表为空 | 低 | 校验不触发 | prompt 中约束回复"暂无数据" |
| ChromaDB 维度不匹配（384维污染） | 低 | RAG 检索失败 | 启动时校验集合维度（1024维） |
| 推荐模块 prompt 过长（含 consult_context） | 中 | LLM 上下文溢出 | consult_context 截断到 500 字 |
| 双写代码文件被 git 回滚 | 低 | DB 与代码不一致 | 启动一致性校验 + 健康检查告警 |
| 前缀 `sess_consult_` 与历史 session 冲突 | 极低 | 历史会话误判 | 检查历史数据，无 sess_consult_ 前缀记录 |

---

## 附录：硬约束与项目规范遵循

本设计严格遵循 project_memory 中的约束：

| 约束 | 设计体现 |
|---|---|
| ChromaDB 必须用 1024 维（BAAI/bge-large-zh-v1.5） | 章节 7 RAG 检索沿用现有集合 |
| 项目仅服务 SCNU | 所有查询限定 college_id=scnu.id |
| 学生基础信息在注册时收集 | users 表已有 region/subjects/score/rank 字段 |
| AI 上下文包含学生基础信息（排除手机号） | 章节 7 slots_summary 明确排除 phone/username |
| 推荐结果限 10 条，60%位次+40%意向 | recommendations 模块保留现有逻辑 |
| Mini-app 默认租户为 SCNU | session 创建 tenant_slug="scnu" |
| Alembic 多 head 冲突线性化 | 章节 8 强调线性 revision 链 |
| 提示词在线编辑集成到现有 AgentSettingsPage | 补充章节 A |
