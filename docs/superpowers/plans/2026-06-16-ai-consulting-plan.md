# Module B: AI 咨询体系 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通 C-end SSE 对话 → LLM 提取 → session_profiles → 分析看板的完整数据链路，并建立准确度测试框架。

**Architecture:** 最小侵入方案 — 新建 `cend_profile_analyzer.py`（独立 C-end LLM 提取器）+ `profile_bridge.py`（桥接层），修改 `miniapp.py` 在 SSE 响应后每 3 轮触发提取，保留旧正则函数作为 fallback。双写 session_profiles 表 + JSON 文件。

**Tech Stack:** Python 3.11 / FastAPI / LangChain / DeepSeek LLM / SQLAlchemy async / PostgreSQL

---

## 文件结构

```
backend/
├── services/
│   ├── cend_profile_analyzer.py    # NEW — C-end LLM 档案提取器
│   ├── profile_bridge.py           # NEW — 桥接层：提取→session_profiles+JSON
│   └── consult_service.py          # UNCHANGED — 旧 regex 函数保留为 fallback
├── api/routes/
│   └── miniapp.py                  # MODIFIED — SSE 结束后触发桥接
├── analytics/
│   └── topic_cloud.py              # MODIFIED — 新增 concerns 数据源
tests/
├── unit/
│   ├── test_cend_profile_analyzer.py  # NEW — 11 tests
│   └── test_profile_bridge.py         # NEW — 4 tests
├── integration/
│   └── test_cend_data_pipeline.py     # NEW — 4 tests
└── benchmarks/
    ├── __init__.py                    # NEW
    ├── knowledge_qa.json              # NEW — >= 100 pairs
    ├── profile_extraction.json        # NEW — >= 50 pairs
    └── run_accuracy.py                # NEW — benchmark script
data/extracted_profiles/               # NEW directory
.github/workflows/backend-ci.yml       # MODIFIED — add benchmark step
.gitignore                             # MODIFIED — add extracted_profiles/
```

---

## HARD RULES（项目强制）

1. **文件写入/编辑**：用 Bash heredoc 创建文件（`cat > path << 'DELIM'`），用 python3 heredoc 修改文件
2. **实现与测试分离**：实现代码和测试代码必须由**不同的子代理实例**编写
3. **TDD 流程**：先写测试 → 确认失败 → 写实现 → 确认通过
4. **AAA 模式**：所有测试必须 `# Arrange` / `# Act` / `# Assert` 注释分隔

---

## Phase 1: B1 C-end 数据链路打通

### Task 1: 新建 `backend/services/cend_profile_analyzer.py`

**Files:** Create: `backend/services/cend_profile_analyzer.py`

**核心代码**（用 Bash heredoc 创建）：

```bash
cat > backend/services/cend_profile_analyzer.py << 'PYEOF'
"""
C-end 档案分析器 — 独立的 LLM 提取器，从学生对话中提取结构化画像。
复用 profile_analyzer.py 的 JSON 解析模式，使用独立的 C-end prompt 模板。

字段体系 (7层):
  basic: {province, subject_type, score}
  interests: {preferred_subjects, strong_subjects, hobbies}
  concerns: list[str] 自由标签
  riasec: {R, I, A, S, E, C} int 1-10
  values: list[str]
  region_pref: {province, city}
  extra: dict
"""
import json, re, logging
from dataclasses import dataclass, field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class CendExtractionResult:
    """C-end 提取结果，映射到 session_profiles.profile_json 的 7 个层级。"""
    basic: dict = field(default_factory=lambda: {"province": "", "subject_type": "", "score": 0})
    interests: dict = field(default_factory=lambda: {"preferred_subjects": [], "strong_subjects": [], "hobbies": []})
    concerns: list = field(default_factory=list)
    riasec: dict = field(default_factory=lambda: {"R": 0, "I": 0, "A": 0, "S": 0, "E": 0, "C": 0})
    values: list = field(default_factory=list)
    region_pref: dict = field(default_factory=lambda: {"province": "", "city": ""})
    extra: dict = field(default_factory=dict)
    completeness: str = "L1"

    def to_profile_json(self) -> dict:
        return {
            "basic": self.basic, "interests": self.interests,
            "concerns": self.concerns, "riasec": self.riasec,
            "values": self.values, "region_pref": self.region_pref, "extra": self.extra,
        }

    def has_any_data(self) -> bool:
        if any(self.basic.values()): return True
        if any(self.interests.get("preferred_subjects", [])): return True
        if any(self.interests.get("strong_subjects", [])): return True
        if any(self.interests.get("hobbies", [])): return True
        if self.concerns: return True
        if any(v > 0 for v in self.riasec.values()): return True
        if self.values: return True
        if any(self.region_pref.values()): return True
        return False


CEND_ANALYZER_PROMPT = """你是一位专业的高考志愿咨询分析员。你的任务是从学生对话中提取画像信息。

## 核心原则
1. 只提取本轮对话中**新出现**的信息，不要重复已有信息
2. 每条提取必须引用学生的**原话**作为依据
3. 找不到新信息就返回空值——不要编造
4. 从学生自然表达中推断，不要强行分类

## RIASEC 维度参考（评分 1-10）
- R (动手操作): 喜欢实验、制作、修理、工具操作
- I (研究思考): 喜欢分析、探索、理论、逻辑推理
- A (艺术创造): 喜欢设计、创作、表达、写作
- S (帮助他人): 喜欢助人、教育、合作、沟通
- E (领导说服): 喜欢管理、组织、说服、竞争
- C (规范有序): 喜欢整理、数据处理、规则遵守

## 价值观分类
可选类别：社会贡献、个人成长、工作稳定、薪资水平、学术氛围、创新机会、工作生活平衡

## 已有画像（不要重复提取）
{existing_profile_summary}

## 输出格式
严格按 JSON 格式输出（不要 markdown 代码块标记）：
{{
  "basic": {{"province": "省份或null", "subject_type": "物理类/历史类或null", "score": "分数或null"}},
  "interests": {{"preferred_subjects": ["意向专业"], "strong_subjects": ["擅长科目"], "hobbies": ["爱好"]}},
  "concerns": ["关注维度自由标签"],
  "riasec": {{"R": null, "I": null, "A": null, "S": null, "E": null, "C": null}},
  "values": ["价值观"],
  "region_pref": {{"province": "偏好省份或null", "city": "偏好城市或null"}},
  "extra": {{}},
  "extraction_notes": ["本轮提取到的具体信息描述，无则空数组"]
}}"""


def _summarize_existing(existing_profile: dict) -> str:
    """将已有画像转为可读摘要，供 prompt 注入。"""
    if not existing_profile or not any(existing_profile.values()):
        return "尚无画像信息"
    lines = []
    basic = existing_profile.get("basic", {})
    if basic:
        parts = []
        if basic.get("province"): parts.append(f"省份={basic['province']}")
        if basic.get("subject_type"): parts.append(f"科类={basic['subject_type']}")
        if basic.get("score"): parts.append(f"分数={basic['score']}")
        if parts: lines.append("基础信息: " + ", ".join(parts))
    interests = existing_profile.get("interests", {})
    if interests:
        parts = []
        if interests.get("preferred_subjects"): parts.append(f"意向专业={interests['preferred_subjects']}")
        if interests.get("strong_subjects"): parts.append(f"擅长科目={interests['strong_subjects']}")
        if parts: lines.append("兴趣: " + ", ".join(parts))
    concerns = existing_profile.get("concerns", [])
    if concerns: lines.append(f"关注维度: {concerns}")
    riasec = existing_profile.get("riasec", {})
    if riasec and any(v > 0 for v in riasec.values()):
        lines.append("RIASEC: " + ", ".join(f"{k}={v}" for k, v in riasec.items() if v > 0))
    values = existing_profile.get("values", [])
    if values: lines.append(f"价值观: {values}")
    return "\n".join(lines) if lines else "尚无画像信息"


def build_cend_analysis_prompt(user_msg: str, ai_reply: str, existing_profile: dict) -> str:
    """构建 C-end 分析 prompt。"""
    summary = _summarize_existing(existing_profile)
    system_prompt = CEND_ANALYZER_PROMPT.format(existing_profile_summary=summary)
    return f"{system_prompt}\n\n## 本轮对话\n学生消息：{user_msg}\nAI回复：{ai_reply}\n\n请分析并输出JSON。"


def parse_cend_response(text: str) -> CendExtractionResult:
    """解析 LLM 响应为 CendExtractionResult。失败时返回空结果。"""
    result = CendExtractionResult()
    if not text: return result
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```\w*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse C-end analyzer response as JSON")
        return result

    basic = data.get("basic", {})
    if basic:
        if basic.get("province"): result.basic["province"] = str(basic["province"])
        if basic.get("subject_type"): result.basic["subject_type"] = str(basic["subject_type"])
        if basic.get("score") is not None:
            try: result.basic["score"] = int(basic["score"])
            except (ValueError, TypeError): pass

    interests = data.get("interests", {})
    if interests:
        if isinstance(interests.get("preferred_subjects"), list):
            result.interests["preferred_subjects"] = interests["preferred_subjects"]
        if isinstance(interests.get("strong_subjects"), list):
            result.interests["strong_subjects"] = interests["strong_subjects"]
        if isinstance(interests.get("hobbies"), list):
            result.interests["hobbies"] = interests["hobbies"]

    concerns = data.get("concerns", [])
    if isinstance(concerns, list): result.concerns = concerns

    riasec_data = data.get("riasec", {})
    if isinstance(riasec_data, dict):
        for dim in ("R", "I", "A", "S", "E", "C"):
            val = riasec_data.get(dim)
            if val is not None:
                try:
                    score = int(val)
                    if 1 <= score <= 10: result.riasec[dim] = score
                except (ValueError, TypeError): pass

    values_data = data.get("values", [])
    if isinstance(values_data, list): result.values = [str(v) for v in values_data if v]

    region = data.get("region_pref", {})
    if isinstance(region, dict):
        if region.get("province"): result.region_pref["province"] = str(region["province"])
        if region.get("city"): result.region_pref["city"] = str(region["city"])

    extra = data.get("extra", {})
    if isinstance(extra, dict): result.extra = extra
    return result


def merge_extraction_results(existing: CendExtractionResult, new_extraction: CendExtractionResult) -> CendExtractionResult:
    """深度合并两次提取结果：新值覆盖旧值，列表去重合并。"""
    merged = CendExtractionResult()
    for key in ("province", "subject_type", "score"):
        new_val = new_extraction.basic.get(key)
        old_val = existing.basic.get(key)
        merged.basic[key] = new_val if new_val else old_val
    for list_key in ("preferred_subjects", "strong_subjects", "hobbies"):
        old_list = existing.interests.get(list_key, [])
        new_list = new_extraction.interests.get(list_key, [])
        seen = set(old_list)
        merged_list = list(old_list)
        for item in new_list:
            if item not in seen: merged_list.append(item); seen.add(item)
        merged.interests[list_key] = merged_list
    seen_concerns = set(existing.concerns)
    merged.concerns = list(existing.concerns)
    for c in new_extraction.concerns:
        if c not in seen_concerns: merged.concerns.append(c); seen_concerns.add(c)
    for dim in ("R", "I", "A", "S", "E", "C"):
        new_val = new_extraction.riasec.get(dim, 0)
        old_val = existing.riasec.get(dim, 0)
        merged.riasec[dim] = new_val if new_val > 0 else old_val
    seen_values = set(existing.values)
    merged.values = list(existing.values)
    for v in new_extraction.values:
        if v not in seen_values: merged.values.append(v); seen_values.add(v)
    merged.region_pref["province"] = new_extraction.region_pref.get("province") or existing.region_pref.get("province", "")
    merged.region_pref["city"] = new_extraction.region_pref.get("city") or existing.region_pref.get("city", "")
    merged.extra = {**existing.extra, **new_extraction.extra}
    merged.completeness = _compute_completeness(merged)
    return merged


def _compute_completeness(result: CendExtractionResult) -> str:
    """按 EvidenceAccumulator 逻辑计算完整度 L1/L2/L3。"""
    riasec_covered = sum(1 for v in result.riasec.values() if v > 0)
    has_values = len(result.values) >= 1
    has_region = bool(result.region_pref.get("province") or result.region_pref.get("city"))
    if riasec_covered >= 4 and has_values: return "L3"
    elif riasec_covered >= 2 and has_region: return "L2"
    return "L1"


async def analyze_cend_turn(user_msg: str, ai_reply: str, existing_profile: dict, conversation_history: list | None = None) -> CendExtractionResult:
    """调用 LLM 分析单轮对话，返回增量提取结果。"""
    llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key,
                     base_url=settings.deepseek_base_url, temperature=0.2)
    prompt = build_cend_analysis_prompt(user_msg, ai_reply, existing_profile)
    system = SystemMessage(content=prompt)
    human = HumanMessage(content="请分析本轮对话并输出JSON。")
    try:
        response = await llm.ainvoke([system, human])
        return parse_cend_response(response.content)
    except Exception as exc:
        logger.error(f"C-end profile analysis failed: {exc}")
        return CendExtractionResult()
PYEOF
```

- [ ] **Step 2: 验证语法**

```bash
cd backend && python -c "from services.cend_profile_analyzer import CendExtractionResult, merge_extraction_results; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/cend_profile_analyzer.py
git commit -m "feat(b1): add cend_profile_analyzer — LLM-based C-end profile extraction"
```

---

### Task 2: 新建 `backend/services/profile_bridge.py`

**Files:** Create: `backend/services/profile_bridge.py`

**核心代码**（用 Bash heredoc 创建）：

```bash
cat > backend/services/profile_bridge.py << 'PYEOF'
"""
桥接层：将 C-end LLM 提取结果写入 session_profiles 表 + JSON 文件备份。
每 3 轮对话触发一次，提取失败不阻塞 SSE 响应。
"""
import json, logging, uuid
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from models import async_session
from models.consult_session import ConsultSession
from models.chat_message import ChatMessage
from tenants.models import SessionProfile
from services.consult_service import update_session_profile
from services.cend_profile_analyzer import analyze_cend_turn, merge_extraction_results, CendExtractionResult
from core.event_writer import write_event

logger = logging.getLogger(__name__)
EXTRACTED_PROFILES_DIR = Path("data/extracted_profiles")


async def get_chat_message_count(session_id: str) -> int:
    """获取指定 session 的用户消息数量。"""
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id, ChatMessage.role == "user")
        )
        return len(result.scalars().all())


async def should_extract(session_id: str) -> bool:
    """判断是否应触发提取：用户消息数 % 3 == 0 且 > 0。"""
    count = await get_chat_message_count(session_id)
    return count > 0 and count % 3 == 0


async def load_existing_profile_json(tenant_id: uuid.UUID, session_id: uuid.UUID) -> Optional[dict]:
    """从 session_profiles 表加载已有 profile_json。"""
    async with async_session() as db:
        result = await db.execute(
            select(SessionProfile).where(
                SessionProfile.tenant_id == tenant_id,
                SessionProfile.session_id == session_id,
            )
        )
        sp = result.scalar_one_or_none()
        return sp.profile_json if sp else None


async def bridge_profile_to_session_profiles(
    session: ConsultSession, tenant_id: uuid.UUID,
    user_content: str, assistant_content: str,
) -> bool:
    """
    主桥接函数：
    1. 加载已有画像 2. LLM 提取 3. Merge 4. 更新 consult_sessions 5. 写入 session_profiles 6. JSON 备份
    Returns: True 如果提取到了新数据
    """
    try:
        existing_json = await load_existing_profile_json(tenant_id, session.id) or {}
        new_extraction = await analyze_cend_turn(
            user_msg=user_content, ai_reply=assistant_content, existing_profile=existing_json,
        )
        existing_result = CendExtractionResult(
            basic=existing_json.get("basic", {}),
            interests=existing_json.get("interests", {}),
            concerns=existing_json.get("concerns", []),
            riasec=existing_json.get("riasec", {}),
            values=existing_json.get("values", []),
            region_pref=existing_json.get("region_pref", {}),
            extra=existing_json.get("extra", {}),
        )
        merged = merge_extraction_results(existing_result, new_extraction)
        if not merged.has_any_data():
            return False

        # Update consult_sessions basic fields
        updates = {}
        if merged.basic.get("province") and not session.province:
            updates["province"] = merged.basic["province"]
        if merged.basic.get("subject_type") and not session.subject_type:
            updates["subject_type"] = merged.basic["subject_type"]
        if merged.basic.get("score") and not session.score:
            updates["score"] = merged.basic["score"]
        if merged.interests.get("preferred_subjects"):
            existing_majors = session.intent_majors or []
            new_majors = [m for m in merged.interests["preferred_subjects"] if m not in existing_majors]
            if new_majors: updates["intent_majors"] = (existing_majors + new_majors)[:10]
        if updates:
            await update_session_profile(session.session_id, updates)

        # Merge to session_profiles table
        profile_json = merged.to_profile_json()
        async with async_session() as db:
            result = await db.execute(
                select(SessionProfile).where(
                    SessionProfile.tenant_id == tenant_id,
                    SessionProfile.session_id == session.id,
                )
            )
            sp = result.scalar_one_or_none()
            if sp:
                sp.profile_json = profile_json
                sp.completeness = merged.completeness
            else:
                sp = SessionProfile(
                    tenant_id=tenant_id, session_id=session.id, user_id=session.user_id,
                    profile_json=profile_json, confidence_json={}, completeness=merged.completeness,
                )
                db.add(sp)
            await db.commit()

        # JSON backup
        EXTRACTED_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        json_path = EXTRACTED_PROFILES_DIR / f"{session.session_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(profile_json, f, ensure_ascii=False, indent=2, default=str)

        # Analytics event
        try:
            await write_event(tenant_id, "profile_extracted", session_id=session.id,
                payload={"completeness": merged.completeness,
                         "riasec_dims_covered": sum(1 for v in merged.riasec.values() if v > 0)})
        except Exception: pass

        logger.info(f"Profile bridged: session={session.session_id} completeness={merged.completeness}")
        return True
    except Exception as exc:
        logger.error(f"bridge_profile failed for {session.session_id}: {exc}")
        return False
PYEOF
```

- [ ] **Step 2: 验证语法**

```bash
cd backend && python -c "from services.profile_bridge import should_extract; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/services/profile_bridge.py
git commit -m "feat(b1): add profile_bridge — bridge LLM extraction to session_profiles + JSON"
```

---

### Task 3: 修改 `backend/api/routes/miniapp.py` — 接入桥接层

**Files:** Modify: `backend/api/routes/miniapp.py`

变更 3 处：import 添加 / 插入桥接调用 / done_data 含 bridge 状态

```bash
python3 << 'PYEOF'
import pathlib
p = pathlib.Path("backend/api/routes/miniapp.py")
content = p.read_text(encoding="utf-8")

# 1. Add import
old_import = "from services.consult_service import (\n    get_or_create_session, get_session, get_chat_history,\n    save_message, update_session_profile,\n    extract_profile_from_message, build_profile_summary,\n)"
new_import = "from services.consult_service import (\n    get_or_create_session, get_session, get_chat_history,\n    save_message, update_session_profile,\n    extract_profile_from_message, build_profile_summary,\n)\nfrom services.profile_bridge import should_extract, bridge_profile_to_session_profiles"
content = content.replace(old_import, new_import)

# 2. Insert bridge call before existing_dict
old_block = """        existing_dict = {
            "province": session.province or "",
            "subject_type": session.subject_type or "",
            "score": session.score or 0,
        }
        profile_updates = await extract_profile_from_message(user_content, full_content, existing_dict)"""

new_block = """        # B1: LLM profile extraction bridge (every 3 turns)
        profile_bridge_ran = False
        try:
            if tenant_id and await should_extract(body.session_id):
                profile_bridge_ran = await bridge_profile_to_session_profiles(
                    session, tenant_id, user_content, full_content
                )
        except Exception as e:
            logging.warning(f"Profile bridge failed for session={body.session_id}: {e}")

        # Fallback: regex extraction for basic fields
        existing_dict = {
            "province": session.province or "",
            "subject_type": session.subject_type or "",
            "score": session.score or 0,
        }
        profile_updates = await extract_profile_from_message(user_content, full_content, existing_dict)"""
content = content.replace(old_block, new_block)

# 3. Update done_data
old_done = """        done_data = {
            "type": "done",
            "session_id": body.session_id,
            "assistant_message": assistant_msg,
            "profile_updated": profile_updated,
            "profile_summary": profile_summary,
        }"""
new_done = """        done_data = {
            "type": "done",
            "session_id": body.session_id,
            "assistant_message": assistant_msg,
            "profile_updated": profile_updated or profile_bridge_ran,
            "profile_summary": profile_summary,
        }"""
content = content.replace(old_done, new_done)

p.write_text(content, encoding="utf-8")
print("miniapp.py updated")
PYEOF
```

验证：`cd backend && python -c "import py_compile; py_compile.compile('api/routes/miniapp.py', doraise=True); print('OK')"`

Commit：`git add backend/api/routes/miniapp.py && git commit -m "feat(b1): integrate profile_bridge into SSE chat — trigger every 3 turns"`

---

### Task 4: 修改 `backend/analytics/topic_cloud.py` — 添加 concerns 数据源

**Files:** Modify: `backend/analytics/topic_cloud.py`

在 `sorted_words` 行之前插入 session_profiles.concerns 查询：

```bash
python3 << 'PYEOF'
import pathlib
p = pathlib.Path("backend/analytics/topic_cloud.py")
content = p.read_text(encoding="utf-8")

old_return = """    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
    return [{"word": w, "count": c} for w, c in sorted_words]"""

new_code = """    # Additional source: concerns from session_profiles.profile_json
    concern_rows = await db.execute(text("""
        SELECT jsonb_array_elements_text(profile_json->'concerns') AS concern_word
        FROM session_profiles
        WHERE tenant_id = :tid
          AND profile_json->'concerns' IS NOT NULL
          AND jsonb_array_length(profile_json->'concerns') > 0
    """), {"tid": tenant_id})
    for row in concern_rows:
        w = row.concern_word.strip()
        if len(w) >= 2:
            word_freq[w] = word_freq.get(w, 0) + 2

    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
    return [{"word": w, "count": c} for w, c in sorted_words]"""

content = content.replace(old_return, new_code)
p.write_text(content, encoding="utf-8")
print("topic_cloud.py updated")
PYEOF
```

Commit：`git add backend/analytics/topic_cloud.py && git commit -m "feat(b1): add session_profiles.concerns data source to topic_cloud"`

---

### Task 5: 更新 `.gitignore` + 创建 `data/extracted_profiles/`

```bash
echo "" >> .gitignore
echo "# Extracted profile JSON backups (dev phase)" >> .gitignore
echo "data/extracted_profiles/" >> .gitignore
mkdir -p data/extracted_profiles
git add .gitignore
git commit -m "chore: add data/extracted_profiles/ to .gitignore"
```

---

## Phase 2: B2 准确度测试框架

### Task 6: 创建 `tests/benchmarks/` 包

```bash
mkdir -p tests/benchmarks
cat > tests/benchmarks/__init__.py << 'PYEOF'
"""Accuracy benchmarks for knowledge base Q&A and profile extraction."""
PYEOF
git add tests/benchmarks/__init__.py
git commit -m "feat(b2): add benchmarks package"
```

---

### Task 7: 创建 `tests/benchmarks/knowledge_qa.json`（>= 100 对）

目标规模 100 对，覆盖 admission_score(30) / curriculum(30) / employment(20) / campus_life(20)。
执行时由子代理基于 `data/approved/` 扩展。初始 10 对样例：

```bash
cat > tests/benchmarks/knowledge_qa.json << 'JSONEOF'
[
  {"id":"kqa_001","question":"华南师范大学2025年计算机科学与技术专业录取分数线是多少？","expected_answer":"该专业2025年在广东省物理类录取最低分约为610分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_002","question":"华师软件工程专业需要多少分？","expected_answer":"软件工程专业2025年在广东物理类录取最低分约为605分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_003","question":"人工智能专业录取分数线","expected_answer":"人工智能专业2025年在广东物理类录取最低分约为615分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_004","question":"电子信息工程多少分能上？","expected_answer":"电子信息工程2025年在广东物理类录取最低分约为595分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_005","question":"数学与应用数学专业的录取分数","expected_answer":"数学与应用数学专业2025年在广东物理类录取最低分约为600分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_006","question":"华师经济学专业分数线","expected_answer":"经济学专业2025年在广东历史类录取最低分约为585分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_007","question":"法学专业录取分数多少？","expected_answer":"法学专业2025年在广东历史类录取最低分约为590分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_008","question":"心理学专业需要多少分？","expected_answer":"心理学专业2025年在广东物理类录取最低分约为590分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_009","question":"汉语言文学专业分数线","expected_answer":"汉语言文学专业2025年在广东历史类录取最低分约为580分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"},
  {"id":"kqa_010","question":"化学专业录取分数线是多少？","expected_answer":"化学专业2025年在广东物理类录取最低分约为585分","source_doc":"data/approved/scnu_admission_2025.json","category":"admission_score"}
]
JSONEOF
git add tests/benchmarks/knowledge_qa.json
git commit -m "feat(b2): add KB Q&A ground truth dataset (10 sample pairs, expand to 100+)"
```

> **执行时扩展**：子代理需扩展至 >= 100 对，按 admission_score(30) / curriculum(30) / employment(20) / campus_life(20) 分布。

---

### Task 8: 创建 `tests/benchmarks/profile_extraction.json`（>= 50 对）

目标规模 50 对。执行时由子代理扩展。初始 5 对样例：

```bash
cat > tests/benchmarks/profile_extraction.json << 'JSONEOF'
[
  {"id":"pe_001","conversation":[{"role":"user","content":"你好，我是广东的高考生，学物理的"},{"role":"assistant","content":"你好！请问你大概考了多少分呢？"},{"role":"user","content":"考了600分，对计算机和人工智能比较感兴趣"},{"role":"assistant","content":"600分很不错！"}],"expected_extraction":{"basic":{"province":"广东","subject_type":"物理类","score":600},"interests":{"preferred_subjects":["计算机","人工智能"],"strong_subjects":[],"hobbies":[]},"concerns":[],"riasec":{"R":0,"I":0,"A":0,"S":0,"E":0,"C":0},"values":[],"region_pref":{"province":"","city":""},"extra":{}}},
  {"id":"pe_002","conversation":[{"role":"user","content":"老师好，我是湖南的历史类考生"},{"role":"assistant","content":"你好！请问你的分数怎么样？"},{"role":"user","content":"考了580分，比较想去师范类专业"},{"role":"assistant","content":"师范类专业很适合历史类考生"},{"role":"user","content":"我语文和英语比较好，喜欢跟人打交道"}],"expected_extraction":{"basic":{"province":"湖南","subject_type":"历史类","score":580},"interests":{"preferred_subjects":["师范"],"strong_subjects":["语文","英语"],"hobbies":[]},"concerns":[],"riasec":{"R":0,"I":0,"A":0,"S":7,"E":0,"C":0},"values":[],"region_pref":{"province":"","city":""},"extra":{}}},
  {"id":"pe_003","conversation":[{"role":"user","content":"浙江的，选的物理化学地理，630分"},{"role":"assistant","content":"浙江630分很优秀！"},{"role":"user","content":"我一直很想学医"},{"role":"assistant","content":"学医是一个很有意义的志向"}],"expected_extraction":{"basic":{"province":"浙江","subject_type":"物理类","score":630},"interests":{"preferred_subjects":["临床医学"],"strong_subjects":["物理","化学","地理"],"hobbies":[]},"concerns":[],"riasec":{"R":0,"I":0,"A":0,"S":8,"E":0,"C":0},"values":[],"region_pref":{"province":"","city":""},"extra":{}}},
  {"id":"pe_004","conversation":[{"role":"user","content":"我是四川的理科生，考了550分"},{"role":"assistant","content":"四川的同学你好！"},{"role":"user","content":"比较迷茫，平时喜欢动手做东西也喜欢研究问题"},{"role":"assistant","content":"喜欢动手和研究说明你可能偏实践和研究型"},{"role":"user","content":"对，高中参加了机器人社团也喜欢数学竞赛"}],"expected_extraction":{"basic":{"province":"四川","subject_type":"物理类","score":550},"interests":{"preferred_subjects":[],"strong_subjects":["数学"],"hobbies":["机器人"]},"concerns":["专业选择迷茫"],"riasec":{"R":7,"I":6,"A":0,"S":0,"E":0,"C":0},"values":[],"region_pref":{"province":"","city":""},"extra":{}}},
  {"id":"pe_005","conversation":[{"role":"user","content":"我是广东考生，历史类590分"},{"role":"assistant","content":"想去哪里读大学呢？"},{"role":"user","content":"想留在广东最好在广州"},{"role":"assistant","content":"广州是个好选择"},{"role":"user","content":"金融和经济，想去银行工作，薪资待遇很重要"}],"expected_extraction":{"basic":{"province":"广东","subject_type":"历史类","score":590},"interests":{"preferred_subjects":["金融","经济学"],"strong_subjects":[],"hobbies":[]},"concerns":["就业前景","薪资待遇"],"riasec":{"R":0,"I":0,"A":0,"S":0,"E":6,"C":5},"values":["薪资水平"],"region_pref":{"province":"广东","city":"广州"},"extra":{}}}
]
JSONEOF
git add tests/benchmarks/profile_extraction.json
git commit -m "feat(b2): add profile extraction ground truth dataset (5 sample pairs, expand to 50+)"
```

---

### Task 9: 创建 `tests/benchmarks/run_accuracy.py`

评测维度：KB LLM-as-judge 1-5（4+正确）/ 提取加权（基础40%+RIASEC30%+兴趣30%）/ 输出 JSON+摘要。

```bash
cat > tests/benchmarks/run_accuracy.py << 'PYEOF'
"""Accuracy benchmarks — KB Q&A (LLM-as-judge) + profile extraction (field comparison)."""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

BENCHMARK_DIR = Path(__file__).parent

def load_json(filename):
    path = BENCHMARK_DIR / filename
    if not path.exists(): print(f"[ERROR] {filename} not found"); sys.exit(1)
    with open(path, encoding="utf-8") as f: return json.load(f)

def fuzzy_match_province(p1, p2):
    if not p1 or not p2: return p1 == p2
    for s in ["省","市","自治区"]: p1, p2 = p1.replace(s,""), p2.replace(s,"")
    return p1 == p2

def jaccard(l1, l2):
    if not l1 and not l2: return 1.0
    s1, s2 = set(l1), set(l2)
    return len(s1&s2)/len(s1|s2) if len(s1|s2) else 0.0

def evaluate_kb_accuracy(dataset):
    from langchain_core.messages import SystemMessage, HumanMessage
    from langchain_openai import ChatOpenAI
    from config import settings
    llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key,
                     base_url=settings.deepseek_base_url, temperature=0.0)
    judge_tpl = "Rate answer quality 1-5.\n5=fully correct\n4=mostly correct\n3=partial\n2=mostly wrong\n1=completely wrong\n\nQuestion: {q}\nExpected: {e}\nActual: {a}\n\nOutput ONLY a digit 1-5."
    scores, details = [], []
    for item in dataset:
        q, exp = item["question"], item["expected_answer"]
        try:
            msgs = [SystemMessage(content="你是华南师范大学招生咨询助手。"), HumanMessage(content=q)]
            actual = llm.invoke(msgs).content
            jmsg = judge_tpl.format(q=q, e=exp, a=actual)
            score = max(1, min(5, int(llm.invoke([HumanMessage(content=jmsg)]).content.strip())))
        except: actual, score = "[ERROR]", 1
        scores.append(score)
        details.append({"id": item["id"], "question": q, "expected": exp, "actual": actual[:500],
                        "score": score, "correct": score>=4, "category": item.get("category","")})
    accuracy = sum(1 for s in scores if s>=4)/len(scores) if scores else 0
    return {"total": len(dataset), "average_score": round(sum(scores)/len(scores),2) if scores else 0,
            "accuracy": round(accuracy,4), "correct_count": sum(1 for s in scores if s>=4), "details": details}

def evaluate_extraction_accuracy(dataset):
    import asyncio
    from services.cend_profile_analyzer import analyze_cend_turn, merge_extraction_results, CendExtractionResult
    basic_scores, riasec_scores, interest_scores, details = [], [], [], []
    for item in dataset:
        conv = item["conversation"]; expected = item["expected_extraction"]
        merged = CendExtractionResult()
        user_msgs = [m for m in conv if m["role"]=="user"]
        ai_msgs = [m for m in conv if m["role"]=="assistant"]
        for i in range(len(user_msgs)):
            try:
                tr = asyncio.get_event_loop().run_until_complete(
                    analyze_cend_turn(user_msgs[i]["content"], ai_msgs[i]["content"] if i<len(ai_msgs) else "", merged.to_profile_json()))
                merged = merge_extraction_results(merged, tr)
            except: pass
        actual = merged.to_profile_json()
        # Basic 40%
        bc = 0
        if fuzzy_match_province(str(expected.get("basic",{}).get("province","")), str(actual.get("basic",{}).get("province",""))): bc+=1
        if str(expected.get("basic",{}).get("subject_type",""))==str(actual.get("basic",{}).get("subject_type","")): bc+=1
        try:
            if abs(int(expected.get("basic",{}).get("score",0) or 0)-int(actual.get("basic",{}).get("score",0) or 0))<=10: bc+=1
        except: pass
        basic_score = bc/3
        basic_scores.append(basic_score)
        # RIASEC 30%
        rc = sum(1 for d in ["R","I","A","S","E","C"] if abs((expected.get("riasec",{}).get(d,0) or 0)-(actual.get("riasec",{}).get(d,0) or 0))<=2)
        riasec_score = rc/6
        riasec_scores.append(riasec_score)
        # Interest/concern 30%
        ic = sum([jaccard(expected.get("interests",{}).get("preferred_subjects",[]), actual.get("interests",{}).get("preferred_subjects",[]))>=0.7,
                  jaccard(expected.get("concerns",[]), actual.get("concerns",[]))>=0.7,
                  jaccard(expected.get("values",[]), actual.get("values",[]))>=0.7])
        interest_score = ic/3
        interest_scores.append(interest_score)
        details.append({"id":item["id"],"expected":expected,"actual":actual,
                        "basic_score":round(basic_score,2),"riasec_score":round(riasec_score,2),"interest_score":round(interest_score,2)})
    avg_b = sum(basic_scores)/len(basic_scores) if basic_scores else 0
    avg_r = sum(riasec_scores)/len(riasec_scores) if riasec_scores else 0
    avg_i = sum(interest_scores)/len(interest_scores) if interest_scores else 0
    return {"total":len(dataset),"basic_accuracy":round(avg_b,4),"riasec_accuracy":round(avg_r,4),
            "interest_accuracy":round(avg_i,4),"weighted_accuracy":round(0.4*avg_b+0.3*avg_r+0.3*avg_i,4),"details":details}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kb-only", action="store_true"); p.add_argument("--extract-only", action="store_true")
    p.add_argument("--output", type=str, default=None)
    args = p.parse_args()
    report = {"timestamp": datetime.now().isoformat(), "kb_accuracy": None, "extract_accuracy": None}
    if not args.extract_only:
        print("="*60+"\nKB Q&A Accuracy\n"+"="*60)
        kb_data = load_json("knowledge_qa.json")
        print(f"Loaded {len(kb_data)} pairs")
        r = evaluate_kb_accuracy(kb_data)
        report["kb_accuracy"] = r["accuracy"]; report["kb_details"] = r
        print(f"Accuracy: {r['accuracy']:.1%} ({r['correct_count']}/{r['total']}) Avg: {r['average_score']}/5")
        print(f"{'PASS' if r['accuracy']>=0.95 else 'FAIL (<95%)'}")
    if not args.kb_only:
        print("\n"+"="*60+"\nProfile Extraction Accuracy\n"+"="*60)
        ext_data = load_json("profile_extraction.json")
        print(f"Loaded {len(ext_data)} pairs")
        r = evaluate_extraction_accuracy(ext_data)
        report["extract_accuracy"] = r["weighted_accuracy"]; report["extract_details"] = r
        print(f"Weighted: {r['weighted_accuracy']:.1%} (Basic: {r['basic_accuracy']:.1%} RIASEC: {r['riasec_accuracy']:.1%} Interest: {r['interest_accuracy']:.1%})")
        print(f"{'PASS' if r['weighted_accuracy']>=0.95 else 'FAIL (<95%)'}")
    print("\n"+"="*60+"\nSUMMARY\n"+"="*60)
    if report["kb_accuracy"] is not None: print(f"KB: {report['kb_accuracy']:.1%} [{'PASS' if report['kb_accuracy']>=0.95 else 'FAIL'}]")
    if report["extract_accuracy"] is not None: print(f"Extract: {report['extract_accuracy']:.1%} [{'PASS' if report['extract_accuracy']>=0.95 else 'FAIL'}]")
    if args.output:
        with open(Path(args.output), "w", encoding="utf-8") as f: json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    overall = (report["kb_accuracy"] is None or report["kb_accuracy"]>=0.95) and (report["extract_accuracy"] is None or report["extract_accuracy"]>=0.95)
    sys.exit(0 if overall else 1)

if __name__=="__main__": main()
PYEOF
```

验证：`cd backend && python -c "import py_compile; py_compile.compile('tests/benchmarks/run_accuracy.py', doraise=True); print('OK')"`

Commit：`git add tests/benchmarks/run_accuracy.py && git commit -m "feat(b2): add accuracy benchmark script"`

---

### Task 10: 修改 CI 添加 benchmark 步骤

```bash
python3 << 'PYEOF'
import pathlib
p = pathlib.Path(".github/workflows/backend-ci.yml")
content = p.read_text(encoding="utf-8")
old = "      - name: Run tests\n        run: python -m pytest tests/ -v"
new = """      - name: Run unit + integration tests
        run: python -m pytest tests/unit/ tests/integration/ -v
      - name: Run accuracy benchmarks
        run: python tests/benchmarks/run_accuracy.py --output accuracy_report.json
        continue-on-error: true
      - name: Check accuracy thresholds
        run: |
          python -c "
import json
try:
    r = json.load(open('accuracy_report.json'))
    kb, ext = r.get('kb_accuracy'), r.get('extract_accuracy')
    warnings = []
    if kb is not None and kb < 0.95: warnings.append(f'KB accuracy {kb:.1%} below 95%')
    if ext is not None and ext < 0.95: warnings.append(f'Extract accuracy {ext:.1%} below 95%')
    for w in warnings: print(f'::warning ::{w}')
    if warnings: print('Accuracy thresholds not met')
    else: print(f'OK: KB={kb:.1% if kb else \"N/A\"}, Extract={ext:.1% if ext else \"N/A\"}')
except FileNotFoundError:
    print('::warning ::accuracy_report.json not found')
"'''
content = content.replace(old, new)
p.write_text(content, encoding="utf-8")
print("backend-ci.yml updated")
PYEOF
```

Commit：`git add .github/workflows/backend-ci.yml && git commit -m "ci(b2): add accuracy benchmark step with 95% threshold warning"`

---

## Phase 3: 测试任务（HARD RULE — 独立子代理编写）

### Test Task A: `tests/unit/test_cend_profile_analyzer.py`（11 tests）

| # | 测试 | 场景 |
|---|------|------|
| 1 | test_parse_valid_json | 正常 JSON |
| 2 | test_parse_markdown_wrapped_json | markdown 包裹 |
| 3 | test_parse_empty_string | 空输入 |
| 4 | test_parse_invalid_json | 非 JSON |
| 5 | test_merge_basic_override | 基础字段覆盖 |
| 6 | test_merge_list_dedup | 列表去重合并 |
| 7 | test_merge_riasec_nonzero_override | RIASEC 非零覆盖 |
| 8 | test_completeness_l3 | 4 RIASEC + values |
| 9 | test_completeness_l2 | 2 RIASEC + region |
| 10 | test_completeness_l1 | 默认 L1 |
| 11 | test_prompt_includes_existing | prompt 含已有画像 |

### Test Task B: `tests/unit/test_profile_bridge.py`（4 tests）

| # | 测试 | 场景 |
|---|------|------|
| 1 | test_should_extract_0_false | 0 消息不触发 |
| 2 | test_should_extract_3_true | 3 条触发 |
| 3 | test_should_extract_4_false | 4 条不触发 |
| 4 | test_should_extract_6_true | 6 条触发 |

### Test Task C: `tests/integration/test_cend_data_pipeline.py`（4 tests）

| # | 测试 | 场景 |
|---|------|------|
| 1 | test_sse_3rd_msg_triggers_bridge | 3 轮触发 |
| 2 | test_session_profiles_written | DB 写入 |
| 3 | test_json_backup_written | JSON 文件 |
| 4 | test_tenant_isolation | 租户隔离 |

### Test Task D: 运行全量测试

```bash
cd backend && python -m pytest tests/ -v --tb=short
```

---

## B3 交互体验优化（Phase 2 — 不在本次执行范围）

B1 的 system prompt 已包含基础心理引导策略（渐进式提问原则）。B3 深化内容：动态提问策略 / UI 确认回显气泡 / 完整度进度条组件。

---

## 验证清单

| # | 验证项 | 方法 | 预期 |
|---|--------|------|------|
| 1 | C-end 数据链路 | mini-app 对话 >=3 轮 → 查 session_profiles | 有记录 |
| 2 | JSON 备份 | `ls data/extracted_profiles/` | 有 {session_id}.json |
| 3 | 分析看板 | GET /api/v1/admin/analytics/profile-dashboard | 有 C-end 数据 |
| 4 | KB 准确度 | `python tests/benchmarks/run_accuracy.py --kb-only` | >= 95% |
| 5 | 提取准确度 | `python tests/benchmarks/run_accuracy.py --extract-only` | >= 95% |
| 6 | 回归测试 | `pytest backend/tests/ -x --tb=short` | 全部通过 |
| 7 | 正则 fallback | 模拟 LLM 不可用 | 基础字段仍可提取 |
