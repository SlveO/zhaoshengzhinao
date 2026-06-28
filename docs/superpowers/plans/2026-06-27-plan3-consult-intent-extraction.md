# Plan 3: Phase 1 意图提取重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把单次 LLM 意图抽取升级为"规则前置 + LLM 增强 + 融合校验"三阶段管道，参考企业知识库问答架构，解决多轮指代、slots 丢失、专业名不规范、LLM 偶发失败等问题。

**Architecture:** 新增 `consult_intent_service.py` 封装三阶段管道；升级 `INTENT_EXTRACTION_PROMPT` 加 history/slots_summary/tenant_majors 占位符；consult.py Phase 1 改为调用 `extract_intent`；新增 tenant 专业词典加载器（TTL 缓存）。

**Tech Stack:** Python 3.11 + LangChain + SQLAlchemy + LRU Cache + TTL

**Spec:** `docs/superpowers/specs/2026-06-27-consult-recommend-enhance-design.md` 章节 2

**前置依赖:** Plan 1 和 Plan 2 已完成（无强依赖，可独立实施，但建议最后执行以避免冲突）

---

## 文件结构

### 新增文件
- `backend/services/consult_intent_service.py` — 意图提取三阶段管道
- `backend/services/tenant_major_dictionary.py` — tenant 专业词典加载器（TTL 缓存）

### 修改文件
- `backend/agents/conversation/prompts_consult.py` — INTENT_EXTRACTION_PROMPT 加占位符
- `backend/api/routes/consult.py` — Phase 1 改用 consult_intent_service.extract_intent

### 新增测试
- `backend/tests/unit/test_consult_intent_service.py`

---

## Task 1: 创建 tenant 专业词典加载器

**Files:**
- Create: `backend/services/tenant_major_dictionary.py`

- [ ] **Step 1: 确认 AdmissionData 模型有 major_name 字段**

Run: `Grep "major_name" backend/models/admission.py -n`
Expected: 找到 `major_name` 字段定义。

- [ ] **Step 2: 写词典加载器文件**

使用 Write 工具创建 `backend/services/tenant_major_dictionary.py`：

```python
"""Tenant 专业词典加载器 — 从 admission_data 表去重提取专业名。

用于咨询意图提取的专业名标准化：把用户的简称/别名映射到 DB 中的标准专业名。
启动时加载，TTL 10 分钟自动刷新。
"""
import asyncio
import logging
import time
from sqlalchemy import select, distinct

from models import async_session
from models.admission import AdmissionData
from models.college import College

_logger = logging.getLogger(__name__)

# 缓存：tenant_slug → (专业名集合, 加载时间戳)
_CACHE: dict[str, tuple[set[str], float]] = {}
_TTL_SECONDS = 600  # 10 分钟
_LOCK = asyncio.Lock()


async def load_tenant_majors(tenant_slug: str) -> set[str]:
    """加载指定 tenant 的专业名集合（TTL 缓存）。

    Args:
        tenant_slug: 租户 slug

    Returns:
        该租户所有专业名的集合；加载失败返回空集合
    """
    now = time.time()
    cached = _CACHE.get(tenant_slug)
    if cached and (now - cached[1]) < _TTL_SECONDS:
        return cached[0]

    async with _LOCK:
        # 双重检查
        cached = _CACHE.get(tenant_slug)
        if cached and (now - cached[1]) < _TTL_SECONDS:
            return cached[0]

        majors: set[str] = set()
        try:
            async with async_session() as db:
                # 通过 tenant 配置的院校名查找 college_id
                from tenants.service import resolve_tenant
                tenant = await resolve_tenant(tenant_slug)
                if not tenant:
                    _logger.warning(f"Tenant not found: {tenant_slug}")
                    return majors

                brand_name = tenant.config.get("brand", {}).get("name", "华南师范大学")
                college_result = await db.execute(
                    select(College).where(College.name == brand_name)
                )
                college = college_result.scalar_one_or_none()
                if not college:
                    _logger.warning(f"College not found for tenant {tenant_slug}: {brand_name}")
                    return majors

                # 查询该院校所有专业名
                result = await db.execute(
                    select(distinct(AdmissionData.major_name)).where(
                        AdmissionData.college_id == college.id
                    )
                )
                for row in result.scalars():
                    if row:
                        majors.add(row.strip())
        except Exception as e:
            _logger.warning(f"load_tenant_majors failed for {tenant_slug}: {e}")

        _CACHE[tenant_slug] = (majors, time.time())
        _logger.info(f"Loaded {len(majors)} majors for tenant {tenant_slug}")
        return majors


def clear_cache(tenant_slug: str | None = None) -> None:
    """清除缓存（测试用）。"""
    if tenant_slug:
        _CACHE.pop(tenant_slug, None)
    else:
        _CACHE.clear()


# 常见专业简称/别名 → 标准名的映射（硬编码补充，DB 不含别名）
ALIAS_MAP: dict[str, str] = {
    "ai": "人工智能",
    "cs": "计算机科学与技术",
    "ce": "计算机科学与技术",
    "se": "软件工程",
    "软工": "软件工程",
    "计科": "计算机科学与技术",
    "计算机": "计算机科学与技术",
    "网安": "网络空间安全",
    "信安": "信息安全",
    "心理学": "应用心理学",
    "光电": "光电信息科学与工程",
    "数学": "数学与应用数学",
    "物理": "物理学",
    "化学": "化学",
    "生科": "生物科学",
    "地科": "地理科学",
    "思政": "思想政治教育",
    "汉语言": "汉语言文学",
    "英语": "英语",
    "教育学": "教育学",
    "学前": "学前教育",
    "小教": "小学教育",
    "特教": "特殊教育",
    "经管": "经济学",
    "金融": "金融学",
    "会计": "会计学",
    "法学": "法学",
}


def normalize_major(raw: str, dictionary: set[str]) -> str | None:
    """把用户输入的专业名标准化为 DB 中的标准名。

    匹配优先级：
    1. 完全匹配 DB 专业名
    2. 别名表匹配
    3. DB 专业名的子串包含（用户说"人工智能"，DB 有"人工智能"）
    4. 用户输入是 DB 专业名的子串（用户说"计算机"，DB 有"计算机科学与技术"）

    Args:
        raw: 用户输入的专业名（已 strip）
        dictionary: DB 专业名集合

    Returns:
        标准化专业名；无法匹配返回 None
    """
    if not raw:
        return None

    raw = raw.strip()

    # 1. 完全匹配
    if raw in dictionary:
        return raw

    # 2. 别名表
    alias = ALIAS_MAP.get(raw.lower()) or ALIAS_MAP.get(raw)
    if alias and alias in dictionary:
        return alias

    # 3. DB 专业名包含用户输入（用户说"人工智能"，DB 有"人工智能"）
    for major in dictionary:
        if raw in major:
            return major

    # 4. 用户输入包含 DB 专业名（用户说"计算机科学与技术专业"，DB 有"计算机科学与技术"）
    for major in dictionary:
        if major in raw:
            return major

    return None
```

- [ ] **Step 3: 验证模块可导入**

Run: `cd backend; python -c "from services.tenant_major_dictionary import load_tenant_majors, normalize_major, ALIAS_MAP; print('import OK, aliases:', len(ALIAS_MAP))"`
Expected: 输出 `import OK, aliases: 28`（或类似数字）。

- [ ] **Step 4: 验证 normalize_major 匹配逻辑**

Run: `cd backend; python -c "from services.tenant_major_dictionary import normalize_major; d = {'人工智能', '计算机科学与技术', '软件工程'}; print(normalize_major('AI', d)); print(normalize_major('软工', d)); print(normalize_major('人工智能', d)); print(normalize_major('计算机', d))"`
Expected: 输出 4 行：`人工智能` / `软件工程` / `人工智能` / `计算机科学与技术`。

- [ ] **Step 5: Commit**

```bash
git add backend/services/tenant_major_dictionary.py
git commit -m "feat(tenant_dictionary): add tenant major dictionary loader with TTL cache and alias normalization"
```

---

## Task 2: 升级 INTENT_EXTRACTION_PROMPT 加占位符

**Files:**
- Modify: `backend/agents/conversation/prompts_consult.py`

- [ ] **Step 1: 读取当前 INTENT_EXTRACTION_PROMPT**

Run: `Read backend/agents/conversation/prompts_consult.py` (limit 25, offset 54)
Expected: 当前 prompt 无 `{history}` `{slots_summary}` `{tenant_majors}` 占位符。

- [ ] **Step 2: 替换 INTENT_EXTRACTION_PROMPT 为升级版**

使用 Edit 工具，old_string 为：
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
new_string 为：
```python
INTENT_EXTRACTION_PROMPT = """你是高考咨询意图分析助手。你的任务有两个：(1) Query Rewriting — 把用户当前消息结合对话历史消解指代，生成一个独立完整的查询；(2) 结构化字段抽取。

## 对话历史（最近 4 轮，用于消解指代）
{history}

## 用户已知基础信息（slots，缺失字段用 null）
{slots_summary}

## 本校已开设专业名（用户提到的专业必须从这个列表中匹配标准名）
{tenant_majors}

## 用户当前消息
{user_content}

## 任务 1：Query Rewriting
把用户当前消息结合对话历史，消解指代生成独立查询。
示例：
- 历史："人工智能专业怎么样" + 当前："那个的录取分呢" → "人工智能专业 录取分"
- 历史："广东考生" + 当前："我能上吗" → "广东考生 录取概率"
- 无历史或无指代 → 原样输出用户消息

## 任务 2：结构化字段抽取
- intent_type: "data_query"(查录取数据/分数/位次) | "policy_query"(查政策/章程/选科要求/培养方案) | "major_intro"(查专业介绍/课程/就业) | "chitchat"(闲聊/问候)
- majors: 标准化专业名数组，必须从「本校已开设专业名」列表中匹配；用户说"AI"应匹配"人工智能"，说"软工"应匹配"软件工程"；无匹配返回空数组 []
- province: 省份名，优先从用户消息提取；缺失时从 slots 取；都无则置 "广东"
- year: 年份整数，从用户消息提取；无则置 null（表示取最新）
- score_query: 用户消息中提到的分数（int 或 null）；缺失时从 slots 取
- rank_query: 用户消息中提到的位次（int 或 null）；缺失时从 slots 取
- need_admission_data: true/false。判定规则：intent_type=data_query 且（用户提到分数/位次 OR majors 非空）时为 true；否则 false
- rewritten_query: 任务 1 的结果（消解指代后的独立查询）

## 输出格式（严格 JSON，不要 markdown 代码块，不要任何其他内容）
{{"intent_type":"data_query","majors":["人工智能"],"province":"广东","year":null,"score_query":585,"rank_query":null,"need_admission_data":true,"rewritten_query":"人工智能专业 录取分"}}
"""
```

- [ ] **Step 3: 验证 prompt 含所有占位符**

Run: `cd backend; python -c "from agents.conversation.prompts_consult import INTENT_EXTRACTION_PROMPT as p; assert '{history}' in p; assert '{slots_summary}' in p; assert '{tenant_majors}' in p; assert '{user_content}' in p; assert '{consult_context}' not in p; print('placeholders OK')"`
Expected: 输出 `placeholders OK`

- [ ] **Step 4: Commit**

```bash
git add backend/agents/conversation/prompts_consult.py
git commit -m "feat(prompts_consult): upgrade INTENT_EXTRACTION_PROMPT with history/slots/tenant_majors placeholders and query rewriting"
```

---

## Task 3: 创建 consult_intent_service.py 三阶段管道

**Files:**
- Create: `backend/services/consult_intent_service.py`

- [ ] **Step 1: 写服务文件**

使用 Write 工具创建 `backend/services/consult_intent_service.py`：

```python
"""咨询意图提取三阶段管道：规则前置 + LLM 增强 + 融合校验。

参考企业知识库问答架构（Dify Query Rewriting、LangChain Multi-Query Retriever、Coze 问题理解节点）。

三阶段：
- 阶段 A：规则前置（同步、零成本）— 提取数字、关键词意图判定、专业词典匹配
- 阶段 B：LLM 增强（temperature=0，含上下文+词典+slots）— Query Rewriting + 结构化抽取
- 阶段 C：融合校验 — 合并规则与 LLM 结果，LLM 失败时规则兜底
"""
import json
import logging
import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config import settings
from services.prompt_service import load_prompt
from services.tenant_major_dictionary import load_tenant_majors, normalize_major

_logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """意图提取结果。"""
    intent_type: str = "chitchat"  # data_query | policy_query | major_intro | chitchat
    majors: list[str] = field(default_factory=list)
    province: str = "广东"
    year: int | None = None
    score_query: int | None = None
    rank_query: int | None = None
    need_admission_data: bool = False
    rewritten_query: str = ""

    def to_dict(self) -> dict:
        return {
            "intent_type": self.intent_type,
            "majors": self.majors,
            "province": self.province,
            "year": self.year,
            "score_query": self.score_query,
            "rank_query": self.rank_query,
            "need_admission_data": self.need_admission_data,
            "rewritten_query": self.rewritten_query,
        }


# ── 阶段 A：规则前置 ──

_INTENT_KEYWORDS = {
    "data_query": ["分数", "位次", "录取", "多少分", "最低分", "投档", "分数线", "排位", "排名"],
    "policy_query": ["政策", "章程", "选科要求", "培养方案", "转专业", "招生计划", "报考条件"],
    "major_intro": ["介绍", "课程", "就业", "怎么样", "学什么", "学啥", "前景", "方向"],
}


def _rule_extract_numbers(text: str) -> tuple[int | None, int | None, int | None, int | None]:
    """规则提取年份、分数、位次。

    Returns:
        (year, score, rank, score_or_rank_mentioned)
    """
    year = None
    score = None
    rank = None

    # 年份：20xx
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        y = int(year_match.group(1))
        if 2020 <= y <= 2030:
            year = y

    # 分数：3 位数（500-750 范围更可能是高考分数）
    score_matches = re.findall(r"\b(\d{3})\b", text)
    for s in score_matches:
        s_int = int(s)
        if 400 <= s_int <= 750:
            score = s_int
            break

    # 位次：4-6 位数（更可能是位次）
    rank_matches = re.findall(r"\b(\d{4,6})\b", text)
    for r in rank_matches:
        r_int = int(r)
        if 1000 <= r_int <= 200000:
            rank = r_int
            break

    score_or_rank_mentioned = bool(score or rank or any(
        kw in text for kw in ["分", "位次", "排名", "排位"]
    ))
    return year, score, rank, score_or_rank_mentioned


def _rule_classify_intent(text: str) -> str | None:
    """规则关键词意图判定。"""
    for intent_type, keywords in _INTENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return intent_type
    return None


def _rule_match_majors(text: str, dictionary: set[str]) -> list[str]:
    """规则匹配专业名（词典正向扫描）。"""
    matched = []
    for major in dictionary:
        if major in text:
            matched.append(major)
    # 也尝试用 normalize_major 匹配别名
    # 简单分词：提取 2-6 字的中文片段
    tokens = re.findall(r"[\u4e00-\u9fa5]{2,8}", text)
    for token in tokens:
        norm = normalize_major(token, dictionary)
        if norm and norm not in matched:
            matched.append(norm)
    return matched[:5]  # 最多 5 个


# ── 阶段 B：LLM 增强 ──

async def _llm_extract_intent(
    user_content: str,
    history: list[dict],
    slots: dict,
    tenant_majors: set[str],
    tenant_slug: str,
    retry_on_parse_fail: bool = True,
) -> dict | None:
    """LLM 调用抽取意图。失败返回 None。"""
    prompt_template = await load_prompt("consult_intent", tenant_slug)

    # 格式化 history
    history_lines = []
    for m in history[-8:]:  # 最近 4 轮 = 8 条消息
        role = "用户" if m["role"] == "user" else "助手"
        history_lines.append(f"{role}: {m['content']}")
    history_text = "\n".join(history_lines) if history_lines else "（无历史）"

    # 格式化 slots
    slots_parts = []
    if slots.get("province"):
        slots_parts.append(f"省份: {slots['province']}")
    if slots.get("subjects"):
        slots_parts.append(f"选科: {slots['subjects']}")
    if slots.get("score"):
        slots_parts.append(f"分数: {slots['score']}")
    if slots.get("rank"):
        slots_parts.append(f"位次: {slots['rank']}")
    slots_text = " | ".join(slots_parts) if slots_parts else "（暂无）"

    # 格式化 tenant_majors
    majors_text = "、".join(sorted(tenant_majors)) if tenant_majors else "（暂无专业数据）"
    if len(majors_text) > 2000:
        majors_text = majors_text[:2000] + "…（截断）"

    try:
        prompt = prompt_template.format(
            history=history_text,
            slots_summary=slots_text,
            tenant_majors=majors_text,
            user_content=user_content,
        )
    except KeyError as e:
        _logger.warning(f"INTENT_EXTRACTION_PROMPT missing placeholder: {e}")
        return None

    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.0,
    )

    try:
        resp = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content="请按格式输出 JSON。")])
        raw = resp.content.strip()
        # 去除 markdown 代码块
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(l for l in lines if not l.startswith("```"))
        return json.loads(raw)
    except json.JSONDecodeError as e:
        _logger.warning(f"Intent JSON parse failed: {e}; raw: {raw[:200] if 'raw' in dir() else 'N/A'}")
        if retry_on_parse_fail:
            _logger.info("Retrying intent extraction with stricter prompt")
            return await _llm_extract_intent(
                user_content, history, slots, tenant_majors, tenant_slug,
                retry_on_parse_fail=False,
            )
        return None
    except Exception as e:
        _logger.warning(f"LLM intent extraction failed: {e}")
        return None


# ── 阶段 C：融合校验 ──

def _fuse(
    rule_intent: str | None,
    rule_majors: list[str],
    rule_year: int | None,
    rule_score: int | None,
    rule_rank: int | None,
    rule_score_mentioned: bool,
    llm_result: dict | None,
    slots: dict,
) -> Intent:
    """融合规则与 LLM 结果。LLM 失败时规则兜底。"""
    if llm_result:
        # LLM 成功，优先 LLM 但用规则补强
        intent_type = llm_result.get("intent_type") or rule_intent or "chitchat"
        llm_majors = llm_result.get("majors") or []
        # 合并专业名（去重）
        majors = list(dict.fromkeys(llm_majors + rule_majors))

        province = llm_result.get("province") or slots.get("province") or "广东"
        year = llm_result.get("year") or rule_year
        score_query = llm_result.get("score_query") or rule_score or slots.get("score")
        rank_query = llm_result.get("rank_query") or rule_rank or slots.get("rank")
        rewritten_query = llm_result.get("rewritten_query") or ""

        # need_admission_data 融合规则：data_query + (分数/位次 OR majors 非空)
        need_admission = False
        if intent_type == "data_query":
            if llm_result.get("need_admission_data") is True:
                need_admission = True
            elif rule_score_mentioned or majors:
                need_admission = True
    else:
        # LLM 失败，纯规则兜底
        intent_type = rule_intent or "chitchat"
        majors = rule_majors
        province = slots.get("province") or "广东"
        year = rule_year
        score_query = rule_score or slots.get("score")
        rank_query = rule_rank or slots.get("rank")
        rewritten_query = ""
        need_admission = (intent_type == "data_query" and (rule_score_mentioned or bool(majors)))

    return Intent(
        intent_type=intent_type,
        majors=majors,
        province=province,
        year=year,
        score_query=score_query,
        rank_query=rank_query,
        need_admission_data=need_admission,
        rewritten_query=rewritten_query,
    )


# ── 主入口 ──

async def extract_intent(
    user_content: str,
    history: list[dict],
    slots: dict,
    tenant_slug: str = "scnu",
) -> Intent:
    """意图提取主入口 — 三阶段管道。

    Args:
        user_content: 用户当前消息
        history: 对话历史 [{role, content}, ...]
        slots: 用户已知信息 {province, subjects, score, rank, ...}
        tenant_slug: 租户 slug

    Returns:
        Intent 对象；任何失败都返回兜底 Intent（不抛异常）
    """
    # 阶段 A：规则前置
    rule_year, rule_score, rule_rank, score_mentioned = _rule_extract_numbers(user_content)
    rule_intent = _rule_classify_intent(user_content)

    try:
        tenant_majors = await load_tenant_majors(tenant_slug)
    except Exception as e:
        _logger.warning(f"load_tenant_majors failed: {e}")
        tenant_majors = set()

    rule_majors = _rule_match_majors(user_content, tenant_majors)

    # 阶段 B：LLM 增强
    llm_result = None
    try:
        llm_result = await _llm_extract_intent(
            user_content=user_content,
            history=history,
            slots=slots,
            tenant_majors=tenant_majors,
            tenant_slug=tenant_slug,
        )
    except Exception as e:
        _logger.warning(f"LLM extract_intent failed: {e}")

    # 阶段 C：融合校验
    intent = _fuse(
        rule_intent=rule_intent,
        rule_majors=rule_majors,
        rule_year=rule_year,
        rule_score=rule_score,
        rule_rank=rule_rank,
        rule_score_mentioned=score_mentioned,
        llm_result=llm_result,
        slots=slots,
    )

    _logger.info(
        "extract_intent: type=%s majors=%s province=%s year=%s need_admission=%s rewritten=%r",
        intent.intent_type, intent.majors, intent.province, intent.year,
        intent.need_admission_data, (intent.rewritten_query or "")[:60],
    )
    return intent
```

- [ ] **Step 2: 验证模块可导入**

Run: `cd backend; python -c "from services.consult_intent_service import extract_intent, Intent; print('import OK')"`
Expected: 输出 `import OK`，无 ImportError。

- [ ] **Step 3: 验证规则函数独立可用**

Run: `cd backend; python -c "from services.consult_intent_service import _rule_extract_numbers, _rule_classify_intent; print(_rule_extract_numbers('2024年考了585分位次32000')); print(_rule_classify_intent('人工智能录取分多少'))"`
Expected: 输出 `(2024, 585, 32000, True)` 和 `data_query`。

- [ ] **Step 4: Commit**

```bash
git add backend/services/consult_intent_service.py
git commit -m "feat(consult_intent): add three-stage intent extraction pipeline (rule + LLM + fusion)"
```

---

## Task 4: consult.py Phase 1 改用 extract_intent

**Files:**
- Modify: `backend/api/routes/consult.py`

- [ ] **Step 1: 读取 consult.py Phase 1 当前实现（第 138-160 行）**

Run: `Read backend/api/routes/consult.py` (limit 25, offset 138)
Expected: Phase 1 含 `_parse_intent_json` 调用、`intent_msgs = [SystemMessage(...), HumanMessage(...)]`、`intent_resp = await llm.ainvoke(intent_msgs)`。

- [ ] **Step 2: 在 consult.py 顶部 import extract_intent**

使用 Edit 工具，old_string 为：
```python
from services.consult_validator import validate_response
from services.prompt_service import load_prompt
```
new_string 为：
```python
from services.consult_validator import validate_response
from services.consult_intent_service import extract_intent
from services.prompt_service import load_prompt
```

- [ ] **Step 3: 替换 Phase 1 的 LLM 调用为 extract_intent 调用**

使用 Edit 工具，old_string 为：
```python
        # ── Phase 1: 意图提取 ──
        yield _sse("thinking", {"status": "正在理解你的问题..."})

        intent_prompt = await load_prompt("consult_intent", body.tenant_slug)
        llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0.0,
        )

        intent = {"intent_type": "chitchat", "majors": [], "need_admission_data": False}
        try:
            intent_msgs = [
                SystemMessage(content=intent_prompt),
                HumanMessage(content=user_content),
            ]
            intent_resp = await llm.ainvoke(intent_msgs)
            intent = _parse_intent_json(intent_resp.content)
        except Exception as e:
            _logger.warning(f"Intent extraction failed: {e}")

        yield _sse("intent", {"intent": intent})
```
new_string 为：
```python
        # ── Phase 1: 意图提取（三阶段管道：规则 + LLM + 融合）──
        yield _sse("thinking", {"status": "正在理解你的问题..."})

        # 准备 extract_intent 所需上下文
        history_for_intent = await get_chat_history(body.session_id, limit=8)
        existing_profile = build_profile_summary(session) or {}
        slots_for_intent = {
            "province": existing_profile.get("province"),
            "subjects": existing_profile.get("subjects"),
            "score": existing_profile.get("score"),
            "rank": existing_profile.get("rank"),
        }

        try:
            intent_obj = await extract_intent(
                user_content=user_content,
                history=history_for_intent,
                slots=slots_for_intent,
                tenant_slug=body.tenant_slug,
            )
            intent = intent_obj.to_dict()
        except Exception as e:
            _logger.warning(f"extract_intent failed: {e}")
            intent = {"intent_type": "chitchat", "majors": [], "need_admission_data": False, "rewritten_query": ""}

        yield _sse("intent", {"intent": intent})
```

- [ ] **Step 4: 保留 _parse_intent_json 函数（向后兼容，可能其他地方用到）**

使用 Grep 检查 `_parse_intent_json` 是否在 consult.py 外被引用：
Run: `Grep "_parse_intent_json" backend/ -n`
Expected: 若仅 consult.py 内引用，可保留函数定义（不删，避免破坏 import）。若其他文件引用，必须保留。

- [ ] **Step 5: 验证 consult.py 语法正确**

Run: `cd backend; python -c "from api.routes.consult import router; print('consult import OK', len(router.routes))"`
Expected: 输出 `consult import OK 1`（POST /api/v1/consult/messages），无 SyntaxError / ImportError。

- [ ] **Step 6: Commit**

```bash
git add backend/api/routes/consult.py
git commit -m "refactor(consult): replace single LLM intent extraction with three-stage pipeline"
```

---

## Task 5: 单元测试 — consult_intent_service

**Files:**
- Test: `backend/tests/unit/test_consult_intent_service.py`

- [ ] **Step 1: 写测试文件**

使用 Write 工具创建 `backend/tests/unit/test_consult_intent_service.py`：

```python
"""consult_intent_service 单元测试。

测试契约（不依赖真实 LLM/DB，mock 所有外部依赖）：
- _rule_extract_numbers: 提取年份/分数/位次
- _rule_classify_intent: 关键词意图判定
- _rule_match_majors: 词典正向匹配 + 别名归一
- _fuse: LLM 成功时合并结果，LLM 失败时规则兜底
- extract_intent: 集成三阶段，LLM 异常时返回兜底 Intent
"""
import pytest
from unittest.mock import patch, AsyncMock
from services.consult_intent_service import (
    _rule_extract_numbers,
    _rule_classify_intent,
    _rule_match_majors,
    _fuse,
    extract_intent,
    Intent,
)


class TestRuleExtractNumbers:
    def test_extract_year_score_rank(self):
        year, score, rank, mentioned = _rule_extract_numbers("2024年考了585分位次32000")
        assert year == 2024
        assert score == 585
        assert rank == 32000
        assert mentioned is True

    def test_extract_year_only(self):
        year, score, rank, mentioned = _rule_extract_numbers("2023年的数据")
        assert year == 2023
        assert score is None
        assert rank is None

    def test_no_numbers(self):
        year, score, rank, mentioned = _rule_extract_numbers("学校怎么样")
        assert year is None
        assert score is None
        assert rank is None
        assert mentioned is False

    def test_score_keyword_mentioned_without_number(self):
        year, score, rank, mentioned = _rule_extract_numbers("录取分数多少")
        assert score is None
        assert mentioned is True  # "分数" 关键词触发

    def test_invalid_year_ignored(self):
        year, _, _, _ = _rule_extract_numbers("1999年的数据")
        assert year is None  # 不在 2020-2030 范围


class TestRuleClassifyIntent:
    def test_data_query(self):
        assert _rule_classify_intent("录取分多少") == "data_query"
        assert _rule_classify_intent("最低位次") == "data_query"

    def test_policy_query(self):
        assert _rule_classify_intent("招生章程") == "policy_query"
        assert _rule_classify_intent("选科要求") == "policy_query"

    def test_major_intro(self):
        assert _rule_classify_intent("专业怎么样") == "major_intro"
        assert _rule_classify_intent("学什么课程") == "major_intro"

    def test_chitchat_no_match(self):
        assert _rule_classify_intent("你好") is None


class TestRuleMatchMajors:
    def test_exact_match(self):
        dictionary = {"人工智能", "计算机科学与技术"}
        result = _rule_match_majors("人工智能专业怎么样", dictionary)
        assert "人工智能" in result

    def test_alias_match(self):
        dictionary = {"人工智能", "软件工程"}
        result = _rule_match_majors("AI专业和软工", dictionary)
        assert "人工智能" in result
        assert "软件工程" in result

    def test_no_match(self):
        dictionary = {"人工智能"}
        result = _rule_match_majors("物理专业", dictionary)
        assert result == []

    def test_max_5_majors(self):
        dictionary = {f"专业{i}" for i in range(10)}
        text = " ".join(f"专业{i}" for i in range(10))
        result = _rule_match_majors(text, dictionary)
        assert len(result) <= 5


class TestFuse:
    def test_llm_success_merges_majors(self):
        llm_result = {
            "intent_type": "data_query",
            "majors": ["人工智能"],
            "province": "广东",
            "year": 2024,
            "need_admission_data": True,
            "rewritten_query": "人工智能 录取分",
        }
        intent = _fuse(
            rule_intent="data_query",
            rule_majors=["计算机科学与技术"],
            rule_year=2024,
            rule_score=585,
            rule_rank=None,
            rule_score_mentioned=True,
            llm_result=llm_result,
            slots={},
        )
        assert intent.intent_type == "data_query"
        assert "人工智能" in intent.majors
        assert "计算机科学与技术" in intent.majors  # 规则补强
        assert intent.year == 2024
        assert intent.score_query == 585
        assert intent.need_admission_data is True
        assert intent.rewritten_query == "人工智能 录取分"

    def test_llm_failure_falls_back_to_rule(self):
        intent = _fuse(
            rule_intent="data_query",
            rule_majors=["人工智能"],
            rule_year=None,
            rule_score=585,
            rule_rank=None,
            rule_score_mentioned=True,
            llm_result=None,
            slots={"province": "广东", "rank": 32000},
        )
        assert intent.intent_type == "data_query"
        assert intent.majors == ["人工智能"]
        assert intent.province == "广东"
        assert intent.score_query == 585
        assert intent.rank_query == 32000
        assert intent.need_admission_data is True  # data_query + 分数提及
        assert intent.rewritten_query == ""

    def test_need_admission_data_inferred_from_rule(self):
        """LLM 标 need_admission_data=false 但规则检测到分数提及 → 强制 true。"""
        llm_result = {
            "intent_type": "data_query",
            "majors": ["人工智能"],
            "need_admission_data": False,
        }
        intent = _fuse(
            rule_intent="data_query",
            rule_majors=[],
            rule_year=None,
            rule_score=585,
            rule_rank=None,
            rule_score_mentioned=True,
            llm_result=llm_result,
            slots={},
        )
        assert intent.need_admission_data is True  # 规则强制

    def test_chitchat_no_admission_data(self):
        llm_result = {"intent_type": "chitchat", "majors": []}
        intent = _fuse(
            rule_intent=None,
            rule_majors=[],
            rule_year=None,
            rule_score=None,
            rule_rank=None,
            rule_score_mentioned=False,
            llm_result=llm_result,
            slots={},
        )
        assert intent.intent_type == "chitchat"
        assert intent.need_admission_data is False


class TestExtractIntent:
    @pytest.mark.asyncio
    async def test_llm_exception_returns_fallback_intent(self):
        """LLM 异常时返回 chitchat 兜底（不抛异常）。"""
        with patch("services.consult_intent_service._llm_extract_intent", side_effect=Exception("LLM down")), \
             patch("services.consult_intent_service.load_tenant_majors", new_callable=AsyncMock, return_value=set()):
            intent = await extract_intent(
                user_content="你好",
                history=[],
                slots={},
                tenant_slug="scnu",
            )
        assert intent.intent_type == "chitchat"
        assert intent.majors == []

    @pytest.mark.asyncio
    async def test_multiline_history_disambiguation(self):
        """多轮指代：历史有"人工智能" + 当前"那个专业分数" → majors 含人工智能。"""
        llm_result = {
            "intent_type": "data_query",
            "majors": ["人工智能"],
            "province": "广东",
            "year": None,
            "need_admission_data": True,
            "rewritten_query": "人工智能专业 录取分",
        }
        with patch("services.consult_intent_service._llm_extract_intent", new_callable=AsyncMock, return_value=llm_result), \
             patch("services.consult_intent_service.load_tenant_majors", new_callable=AsyncMock, return_value={"人工智能"}):
            intent = await extract_intent(
                user_content="那个专业分数多少",
                history=[{"role": "user", "content": "人工智能怎么样"}, {"role": "assistant", "content": "..."}],
                slots={"province": "广东"},
                tenant_slug="scnu",
            )
        assert intent.intent_type == "data_query"
        assert "人工智能" in intent.majors
        assert intent.rewritten_query == "人工智能专业 录取分"

    @pytest.mark.asyncio
    async def test_slots_fallback_when_llm_missing_score(self):
        """LLM 未抽到 score 但 slots 有 → 从 slots 取。"""
        llm_result = {
            "intent_type": "data_query",
            "majors": ["人工智能"],
            "province": "广东",
            "score_query": None,  # LLM 没抽到
            "need_admission_data": True,
        }
        with patch("services.consult_intent_service._llm_extract_intent", new_callable=AsyncMock, return_value=llm_result), \
             patch("services.consult_intent_service.load_tenant_majors", new_callable=AsyncMock, return_value={"人工智能"}):
            intent = await extract_intent(
                user_content="我能上吗",
                history=[],
                slots={"province": "广东", "score": 585, "rank": 32000},
                tenant_slug="scnu",
            )
        assert intent.score_query == 585  # 从 slots 兜底
        assert intent.rank_query == 32000
```

- [ ] **Step 2: 运行单元测试**

Run: `cd backend; python -m pytest tests/unit/test_consult_intent_service.py -v`
Expected: 全部 PASS（约 16 个测试）。

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_consult_intent_service.py
git commit -m "test(consult_intent): unit tests for three-stage intent extraction pipeline"
```

---

## Task 6: 端到端验证 — 咨询多轮对话准确率

- [ ] **Step 1: 重启后端服务**

在 terminal_id: 6 按 Ctrl+C 停止 uvicorn，重新运行：
Run: `cd backend; uvicorn main:app --host 127.0.0.1 --port 8000 --reload`
Expected: 启动无错误，日志含 `Loaded N majors for tenant scnu`。

- [ ] **Step 2: 验证 tenant 词典加载**

后端启动后，触发一次咨询请求，观察日志：
```
INFO:services.tenant_major_dictionary:Loaded N majors for tenant scnu
INFO:services.consult_intent_service:extract_intent: type=data_query majors=['人工智能'] ...
```
Expected: N > 0（如 50+ 专业名）。

- [ ] **Step 3: 多轮对话测试**

使用 curl 或 mini-app 实测：
```bash
# 1. 创建咨询会话
$sessionId = "sess_consult_" + [guid]::NewGuid().ToString()
# 2. 第一轮："人工智能专业怎么样"
# 3. 第二轮："那个的录取分呢"
# 4. 第三轮："我这个分能上吗"（需先在 slots 填 score=585）
```
Expected:
- 第二轮 intent.majors 含"人工智能"（多轮指代消解）
- 第三轮 need_admission_data=true（slots 兜底 + 规则强制）

- [ ] **Step 4: 验证 SSE intent 事件含 rewritten_query**

观察 SSE 流的 `intent` 事件：
```
data: {"type":"intent","intent":{"intent_type":"data_query","majors":["人工智能"],"rewritten_query":"人工智能专业 录取分",...}}
```
Expected: `rewritten_query` 字段非空。

- [ ] **Step 5: 记录验证结果到 session memory**

记录：
- tenant 词典加载成功，N 个专业 ✓
- 多轮指代消解有效 ✓
- slots 兜底生效 ✓
- LLM 失败降级为规则结果 ✓
- SSE intent 事件含 rewritten_query ✓

---

## Self-Review 检查

**Spec 覆盖：**
- 章节 2.3 处理流程（阶段 A/B/C/D）→ Task 3 ✓
- 章节 2.4 Intent 数据结构 → Task 3 ✓
- 章节 2.5 新增文件 consult_intent_service.py → Task 3 ✓
- 章节 2.6 改造点（consult.py + prompts_consult.py + tenant 词典）→ Task 1, 2, 4 ✓
- 章节 2.7 预期效果（多轮/slots/词典/LLM 失败/need_admission_data）→ Task 5 测试覆盖 ✓
- 章节 6 测试策略（意图提取单测）→ Task 5 ✓
- 章节 7 验收 #5, #6, #7 → Task 6 ✓

**Placeholder 扫描：** 无 TBD/TODO，所有步骤含完整代码。

**Type 一致性：**
- `Intent` dataclass 在 Task 3 定义，Task 4/5 使用一致
- `extract_intent(user_content, history, slots, tenant_slug)` 签名在 Task 3/4/5 一致
- `load_tenant_majors(tenant_slug)` 在 Task 1/3 一致
- `normalize_major(raw, dictionary)` 在 Task 1/3 一致
- INTENT_EXTRACTION_PROMPT 占位符 `{history}` `{slots_summary}` `{tenant_majors}` `{user_content}` 在 Task 2/3 一致

**风险点：**
- Task 4 Step 3 的 Edit old_string 必须与 consult.py 当前代码完全一致 — 实施时先 Read 确认。
- Task 3 Step 1 的 `_llm_extract_intent` 内部递归重试需确保 `retry_on_parse_fail=False` 终止条件正确 — 已在代码中处理。
- Task 6 Step 3 的多轮测试需手动操作 mini-app 或 curl，无法完全自动化 — 记录到 session memory 即可。
- `_rule_match_majors` 的分词正则 `[\u4e00-\u9fa5]{2,8}` 可能误匹配非专业词（如"怎么样"）— 但 `normalize_major` 会过滤无法匹配的词，影响可控。

**与 Plan 1/2 的兼容性：**
- Plan 3 不修改 Plan 1/2 涉及的文件（prompts_b2b.py / chat.py / recommendation_service.py）
- Plan 3 修改 prompts_consult.py 的 INTENT_EXTRACTION_PROMPT，与 Plan 1 修改的 CONSULT_SYSTEM_PROMPT 是不同常量，无冲突
- Plan 3 新增 consult_intent_service.py，与 Plan 2 的 recommend_retrieval_service.py 完全独立
