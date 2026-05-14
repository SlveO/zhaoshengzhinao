# Profile Building System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword-based slot extraction with evidence-driven profile building — new ProfileAnalyzer Agent + EvidenceAccumulator, adaptive stage progression, and recommendation integration.

**Architecture:** Two new modules (profile_analyzer.py, evidence_accumulator.py) form the analysis track. The conversation agent remains the dialog track. chat.py orchestrates both sequentially per turn. slot_filler.py becomes a thin backwards-compat wrapper. Frontend SlotProgress rewrites to EvidenceProgress with RIASEC hex-grid visualization.

**Tech Stack:** Python 3.11, LangChain ChatOpenAI (DeepSeek), Redis, FastAPI WebSocket, React 18 + TypeScript + Zustand + Tailwind CSS

---

## File Map

| Unit | Responsibility | Dependencies |
|------|---------------|-------------|
| `evidence_accumulator.py` (new) | Store/retrieve evidence entries, compute confidence, detect blind spots, build profile snapshot | Redis (via chat_service), config |
| `profile_analyzer.py` (new) | LLM call with JSON schema structured output to extract evidence from conversation turns | LangChain ChatOpenAI, config, evidence_accumulator |
| `slot_filler.py` (rewrite) | Thin backwards-compat wrapper — delegates to evidence_accumulator | evidence_accumulator |
| `agent.py` (modify) | Remove _SLOT_PATTERN, _fallback_extract, add blind_spot_hints injection | profile_analyzer, evidence_accumulator, prompts |
| `chat.py` (modify) | Wire profile_analyzer after conversation agent, new _determine_next_stage, fix confirm→done summary | profile_analyzer, evidence_accumulator, agent |
| `recommendation_service.py` (modify) | Adaptive RANKING_PROMPT based on L1-L4 completeness | evidence_accumulator |
| `recommendation.py` (modify) | Cache invalidation on evidence update, use evidence for snapshot | evidence_accumulator, redis |
| `SlotProgress.tsx` → `EvidenceProgress.tsx` | RIASEC 6-dim hex status + confidence rings + completeness badge | chatStore |
| `SummaryModal.tsx` (modify) | Show evidence items (user quotes + inferred values) | chatStore |
| `ProfileSummaryBar.tsx` (modify) | Add L1-L4 completeness badge + "return to chat" prompt | recommendationStore |
| `types/index.ts` (modify) | Add EvidenceItem, DimensionState, RIASEC hex types | — |

---

### Task 1: Evidence Accumulator — Core Data Structure

**Files:**
- Create: `backend/agents/conversation/evidence_accumulator.py`
- Create: `backend/tests/test_evidence_accumulator.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_evidence_accumulator.py
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.conversation.evidence_accumulator import (
    EvidenceAccumulator, RIASEC_DIMS, VALUES_CATEGORIES, compute_completeness
)


class TestEvidenceAccumulator:
    def test_add_evidence_creates_dimension(self):
        acc = EvidenceAccumulator()
        evt = acc.add_evidence(
            dimension="riasec_I",
            source_turn=3,
            user_quote="我特别喜欢自己查资料研究不明白的东西",
            inferred_score=8,
            rationale="学生表达了对独立研究的明确兴趣",
            confidence=0.6,
        )
        assert evt["id"].startswith("evt_")
        assert evt["dimension"] == "riasec_I"
        state = acc.get_dimension_state("riasec_I")
        assert state["evidence_count"] == 1
        assert state["score"] == 8.0
        assert state["confidence"] == 0.6

    def test_multiple_evidence_weights_average(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "research stuff", 8, "reason", 0.6)
        acc.add_evidence("riasec_I", 3, "analyzes math", 6, "reason", 0.8)
        state = acc.get_dimension_state("riasec_I")
        assert state["evidence_count"] == 2
        # Weighted: (8*0.6 + 6*0.8) / (0.6+0.8) = (4.8+4.8)/1.4 = 6.86
        assert round(state["score"], 1) == 6.9
        # Aggregated confidence: min(0.5 + 2*0.08, 0.9) = 0.66, but also weight avg 1.4/2=0.7
        assert state["confidence"] > 0.6

    def test_detect_blind_spots(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "x", 7, "r", 0.5)
        acc.add_evidence("riasec_S", 2, "y", 8, "r", 0.5)
        blind = acc.detect_blind_spots()
        assert "riasec_R" in blind
        assert "riasec_A" in blind
        assert "riasec_E" in blind
        assert "riasec_C" in blind
        assert "riasec_I" not in blind
        assert "riasec_S" not in blind

    def test_export_snapshot(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "x", 7, "r", 0.5)
        acc.add_evidence("riasec_S", 2, "y", 8, "r", 0.5)
        # Set region and score via seed
        acc.seed_basics(score=620, subjects="物化生", region=["广东"])
        snap = acc.export_snapshot()
        assert snap["score"] == 620
        assert snap["subjects"] == "物化生"
        assert snap["region_pref"] == ["广东"]
        assert "I" in snap["riasec"]
        assert "S" in snap["riasec"]
        assert snap["completeness"] == "L2"  # 2 RIASEC + region


class TestComputeCompleteness:
    def test_l1_basic(self):
        evidence = make_evidence(riasec_covered=0, has_values=False, has_region=False)
        assert compute_completeness(evidence) == "L1"

    def test_l2_moderate(self):
        evidence = make_evidence(riasec_covered=2, has_values=False, has_region=True)
        assert compute_completeness(evidence) == "L2"

    def test_l3_deep(self):
        evidence = make_evidence(riasec_covered=4, has_values=True, has_region=True)
        assert compute_completeness(evidence) == "L3"


def make_evidence(riasec_covered, has_values, has_region):
    riasec_keys = ["riasec_R", "riasec_I", "riasec_A", "riasec_S", "riasec_E", "riasec_C"]
    ev = {}
    for i, k in enumerate(riasec_keys):
        ev[k] = {"evidence_count": 1 if i < riasec_covered else 0, "confidence": 0.7 if i < riasec_covered else 0}
    ev["values"] = {"evidence_count": 2 if has_values else 0}
    ev["region_pref"] = {"regions": ["广东"]} if has_region else {}
    return ev
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_evidence_accumulator.py -v`
Expected: FAIL with "No module named 'agents.conversation.evidence_accumulator'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/agents/conversation/evidence_accumulator.py
"""Evidence-driven profile building — stores evidence entries, computes confidence, detects blind spots."""
import uuid
from typing import Optional

RIASEC_DIMS = {
    "riasec_R": "动手操作",
    "riasec_I": "研究思考",
    "riasec_A": "艺术创造",
    "riasec_S": "帮助他人",
    "riasec_E": "领导说服",
    "riasec_C": "规范有序",
}

VALUES_CATEGORIES = ["社会贡献", "个人成长", "工作稳定", "薪资水平"]

RIASEC_KEYS = list(RIASEC_DIMS.keys())


class EvidenceAccumulator:
    def __init__(self, seed: Optional[dict] = None):
        self._evidence: dict = {}
        for k in RIASEC_KEYS:
            self._evidence[k] = {"evidence": [], "evidence_count": 0, "confidence": 0.0}
        self._evidence["values"] = {"evidence": [], "evidence_count": 0, "ranked": []}
        self._evidence["region_pref"] = {"regions": []}
        self._evidence["score"] = {"value": None}
        self._evidence["subjects"] = {"value": None}
        self._evidence["engagement"] = {"trust_level": "low", "willingness_to_share": 0.0, "indicators": []}
        if seed:
            self.seed_basics(**seed)

    def seed_basics(self, score: Optional[int] = None, subjects: Optional[str] = None, region: Optional[list] = None):
        if score:
            self._evidence["score"] = {"value": score, "evidence_count": 1, "confidence": 1.0}
        if subjects:
            self._evidence["subjects"] = {"value": subjects, "evidence_count": 1, "confidence": 1.0}
        if region:
            self._evidence["region_pref"]["regions"] = region

    def add_evidence(self, dimension: str, source_turn: int, user_quote: str,
                     inferred_score: int, rationale: str, confidence: float) -> dict:
        item = {
            "id": f"evt_{uuid.uuid4().hex[:8]}",
            "dimension": dimension,
            "source_turn": source_turn,
            "user_quote": user_quote,
            "inferred_value": {"dimension": dimension, "score": inferred_score, "rationale": rationale},
            "confidence": confidence,
        }
        self._evidence[dimension]["evidence"].append(item)
        self._evidence[dimension]["evidence_count"] = len(self._evidence[dimension]["evidence"])
        self._recalc_dimension(dimension)
        return item

    def _recalc_dimension(self, dimension: str):
        items = self._evidence[dimension]["evidence"]
        if not items:
            return
        total_weight = sum(e["confidence"] for e in items)
        if total_weight > 0:
            weighted_score = sum(e["inferred_value"]["score"] * e["confidence"] for e in items) / total_weight
        else:
            weighted_score = sum(e["inferred_value"]["score"] for e in items) / len(items)
        self._evidence[dimension]["score"] = round(weighted_score, 1)
        n = len(items)
        if n == 1:
            agg_conf = items[0]["confidence"]
        else:
            agg_conf = min(0.5 + n * 0.08, 0.95)
        self._evidence[dimension]["confidence"] = round(agg_conf, 2)

    def get_dimension_state(self, dimension: str) -> dict:
        entry = self._evidence.get(dimension, {})
        return {
            "dimension": dimension,
            "label": RIASEC_DIMS.get(dimension, ""),
            "score": entry.get("score"),
            "evidence_count": entry.get("evidence_count", 0),
            "confidence": entry.get("confidence", 0.0),
            "evidence": entry.get("evidence", []),
        }

    def detect_blind_spots(self) -> list[str]:
        hints = []
        for dim_key, label in RIASEC_DIMS.items():
            if self._evidence[dim_key]["evidence_count"] == 0:
                hints.append(dim_key)
        return hints

    def set_engagement(self, trust_level: str, willingness: float, indicators: list[str]):
        self._evidence["engagement"] = {
            "trust_level": trust_level,
            "willingness_to_share": willingness,
            "indicators": indicators,
        }

    def set_values(self, ranked: list[str]):
        self._evidence["values"]["ranked"] = ranked
        self._evidence["values"]["evidence_count"] = len(ranked)

    def export_snapshot(self) -> dict:
        riasec = {}
        for k in RIASEC_KEYS:
            state = self.get_dimension_state(k)
            if state["score"] is not None:
                riasec[k.replace("riasec_", "")] = state["score"]
        return {
            "score": self._evidence["score"].get("value"),
            "subjects": self._evidence["subjects"].get("value"),
            "region_pref": self._evidence["region_pref"].get("regions", []),
            "riasec": riasec,
            "values": self._evidence["values"].get("ranked", []),
            "completeness": compute_completeness(self._evidence),
            "engagement": self._evidence.get("engagement", {}),
        }

    def to_dict(self) -> dict:
        return self._evidence

    @classmethod
    def from_dict(cls, data: dict) -> "EvidenceAccumulator":
        acc = cls()
        for k in RIASEC_KEYS:
            if k in data:
                acc._evidence[k] = data[k]
        for k in ["values", "region_pref", "score", "subjects", "engagement"]:
            if k in data:
                acc._evidence[k] = data[k]
        return acc


def compute_completeness(evidence: dict) -> str:
    riasec_covered = sum(1 for d in RIASEC_KEYS if evidence[d]["evidence_count"] > 0)
    has_values = evidence.get("values", {}).get("evidence_count", 0) >= 1
    has_region = bool(evidence.get("region_pref", {}).get("regions"))

    if riasec_covered >= 4 and has_values:
        return "L3"
    elif riasec_covered >= 2 and has_region:
        return "L2"
    return "L1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_evidence_accumulator.py -v`
Expected: PASS (4 tests passing)

- [ ] **Step 5: Commit**

```bash
git add backend/agents/conversation/evidence_accumulator.py backend/tests/
git commit -m "feat: add EvidenceAccumulator with weighted scoring and blind spot detection"
```

---

### Task 2: Profile Analyzer Agent

**Files:**
- Create: `backend/agents/conversation/profile_analyzer.py`
- Create: `backend/tests/test_profile_analyzer.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_profile_analyzer.py
import pytest, json
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agents.conversation.profile_analyzer import (
    build_analysis_prompt, parse_analysis_response, PROFILE_ANALYZER_SCHEMA
)
from agents.conversation.evidence_accumulator import EvidenceAccumulator


class TestParseAnalysisResponse:
    def test_parse_valid_evidence_extraction(self):
        response_text = json.dumps({
            "new_evidence": [
                {
                    "dimension": "riasec_I",
                    "user_quote": "我喜欢研究数学题",
                    "inferred_score": 8,
                    "rationale": "学生表达了对分析和研究的兴趣",
                    "confidence": 0.75
                }
            ],
            "values_hint": "个人成长",
            "region_mentioned": None,
            "engagement_assessment": {
                "trust_level": "medium",
                "willingness_to_share": 0.6,
                "indicators": ["学生主动分享了个人经历"]
            }
        })
        result = parse_analysis_response(response_text)
        assert len(result["new_evidence"]) == 1
        assert result["new_evidence"][0]["dimension"] == "riasec_I"
        assert result["engagement_assessment"]["trust_level"] == "medium"

    def test_parse_empty_response(self):
        response_text = json.dumps({
            "new_evidence": [],
            "values_hint": None,
            "region_mentioned": None,
            "engagement_assessment": {
                "trust_level": "low",
                "willingness_to_share": 0.3,
                "indicators": []
            }
        })
        result = parse_analysis_response(response_text)
        assert len(result["new_evidence"]) == 0

    def test_parse_malformed_json_returns_empty(self):
        result = parse_analysis_response("not valid json {{")
        assert len(result["new_evidence"]) == 0
        assert result["engagement_assessment"]["trust_level"] == "low"

    def test_parse_json_inside_markdown(self):
        inner = json.dumps({"new_evidence": [], "values_hint": None, "region_mentioned": "广东",
                            "engagement_assessment": {"trust_level": "low", "willingness_to_share": 0.2, "indicators": []}})
        response_text = f"```json\n{inner}\n```"
        result = parse_analysis_response(response_text)
        assert result["region_mentioned"] == "广东"


class TestBuildAnalysisPrompt:
    def test_includes_blind_spot_hints(self):
        acc = EvidenceAccumulator()
        acc.add_evidence("riasec_I", 1, "x", 7, "r", 0.5)
        blind_spots = acc.detect_blind_spots()
        prompt = build_analysis_prompt("用户说的话...", "AI的回复...", acc.to_dict(), blind_spots)
        assert "用户说的话" in prompt
        assert "riasec_R" in prompt  # blind spot mentioned
        assert "riasec_I" not in prompt.split("未探索维度")[1] if "未探索维度" in prompt else True
```

- [ ] **Step 2: Run test**

Run: `cd backend && python -m pytest tests/test_profile_analyzer.py -v`
Expected: FAIL with import error

- [ ] **Step 3: Write implementation**

```python
# backend/agents/conversation/profile_analyzer.py
"""Profile Analyzer — standalone LLM agent that extracts evidence from conversation turns."""
import json, re
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.evidence_accumulator import RIASEC_DIMS, RIASEC_KEYS

ANALYZER_SYSTEM_PROMPT = """你是一位专业的心理学评估分析员。你的任务是从对话中提取用户画像证据。

## 核心原则
1. 只提取本轮对话中**新出现**的证据，不要重复已有证据
2. 每条证据必须引用用户的**原话**
3. 找不到新证据就返回空列表——不要编造
4. 参与度评估要基于用户本轮的回应质量

## RIASEC 维度参考
- R (动手操作): 实验、制作、修理、工具操作、组装
- I (研究思考): 分析、探索、理论、逻辑推理、钻研问题
- A (艺术创造): 设计、创作、表达、想象、写作、绘画
- S (帮助他人): 助人、教育、志愿服务、合作、沟通
- E (领导说服): 管理、组织、说服、竞争、商业思维
- C (规范有序): 整理、数据处理、规则遵守、会计、条理

## 参与度评估标准
- low: 学生回答敷衍（"不知道""随便""都行"），回避开放式问题
- medium: 学生给出具体回答，有一定细节，愿意参与对话
- high: 学生主动分享经历，表达真实情感，回答内容丰富

## 已有证据（不要重复）
{existing_evidence}

## 未探索维度提示
{blind_spot_hint}

## 输出格式
严格按 JSON 格式输出（不要 markdown 代码块标记）：
{{
  "new_evidence": [
    {{
      "dimension": "riasec_X",
      "user_quote": "用户原话",
      "inferred_score": 7,
      "rationale": "推断理由",
      "confidence": 0.7
    }}
  ],
  "values_hint": "价值观关键词或null",
  "region_mentioned": "提及的地区或null",
  "engagement_assessment": {{
    "trust_level": "low/medium/high",
    "willingness_to_share": 0.5,
    "indicators": ["具体指标"]
  }}
}}"""


def build_analysis_prompt(user_msg: str, ai_reply: str, existing_evidence: dict, blind_spots: list[str]) -> str:
    evidence_summary = _summarize_evidence(existing_evidence)
    blind_hint = ""
    if blind_spots:
        labels = [f"{k}({RIASEC_DIMS.get(k, '')})" for k in blind_spots]
        blind_hint = f"注意：以下维度尚无证据，优先从本轮对话中识别：{', '.join(labels)}"
    else:
        blind_hint = "所有 RIASEC 维度均已覆盖，关注价值观和深层次偏好。"
    return ANALYZER_SYSTEM_PROMPT.format(
        existing_evidence=evidence_summary,
        blind_spot_hint=blind_hint,
    )


def _summarize_evidence(evidence: dict) -> str:
    lines = []
    for k in RIASEC_KEYS:
        e = evidence.get(k, {})
        if e.get("evidence_count", 0) > 0:
            lines.append(f"- {k}: {e['evidence_count']}条证据, 当前评分{e.get('score')}, 置信度{e.get('confidence')}")
    values = evidence.get("values", {})
    if values.get("ranked"):
        lines.append(f"- 价值观: {' > '.join(values['ranked'])}")
    return "\n".join(lines) if lines else "尚无证据"


def parse_analysis_response(text: str) -> dict:
    """Parse LLM response. Returns dict with new_evidence, values_hint, region_mentioned, engagement_assessment."""
    default = {
        "new_evidence": [],
        "values_hint": None,
        "region_mentioned": None,
        "engagement_assessment": {"trust_level": "low", "willingness_to_share": 0.3, "indicators": []},
    }
    # Strip markdown code blocks
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default

    result = {
        "new_evidence": data.get("new_evidence", []),
        "values_hint": data.get("values_hint"),
        "region_mentioned": data.get("region_mentioned"),
        "engagement_assessment": data.get("engagement_assessment", default["engagement_assessment"]),
    }
    # Validate evidence items
    valid_evidence = []
    for item in result["new_evidence"]:
        if item.get("dimension") in RIASEC_KEYS and item.get("user_quote"):
            valid_evidence.append(item)
    result["new_evidence"] = valid_evidence
    return result


async def analyze_turn(user_msg: str, ai_reply: str, evidence: dict, blind_spots: list[str]) -> dict:
    """Call LLM to analyze a conversation turn and return parsed evidence."""
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.2,
    )
    system = SystemMessage(content=build_analysis_prompt(user_msg, ai_reply, evidence, blind_spots))
    human = HumanMessage(content=f"本轮用户消息：{user_msg}\n\nAI回复：{ai_reply}\n\n请分析并输出JSON。")
    try:
        response = await llm.ainvoke([system, human])
        return parse_analysis_response(response.content)
    except Exception:
        return parse_analysis_response("")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_profile_analyzer.py -v`
Expected: PASS (5 tests passing, LLM call not tested in unit)

- [ ] **Step 5: Commit**

```bash
git add backend/agents/conversation/profile_analyzer.py backend/tests/test_profile_analyzer.py
git commit -m "feat: add ProfileAnalyzer agent with structured JSON output and engagement assessment"
```

---

### Task 3: Rewrite slot_filler.py as Compatibility Layer

**Files:**
- Modify: `backend/agents/conversation/slot_filler.py`

- [ ] **Step 1: Rewrite slot_filler.py**

```python
# backend/agents/conversation/slot_filler.py
"""Backwards-compatible wrapper — delegates to EvidenceAccumulator."""
from agents.conversation.evidence_accumulator import EvidenceAccumulator


def merge_slots(existing: dict, update: dict) -> dict:
    """DEPRECATED: Used only for old code paths. New code should use EvidenceAccumulator directly."""
    acc = EvidenceAccumulator.from_dict(existing) if existing else EvidenceAccumulator()
    riasec_update = update.get("riasec_update") or {}
    if isinstance(riasec_update, dict):
        for dim, val in riasec_update.items():
            key = f"riasec_{dim}"
            if val is not None and key in acc.to_dict():
                acc.add_evidence(key, 0, "", int(val), "keyword fallback", 0.3)
    if update.get("values_hint"):
        existing_vals = acc.to_dict().get("values", {}).get("ranked", [])
        if update["values_hint"] not in existing_vals:
            existing_vals.append(update["values_hint"])
        acc.set_values(existing_vals)
    if update.get("region_pref"):
        existing_regions = set(acc.to_dict().get("region_pref", {}).get("regions", []))
        existing_regions.update(update["region_pref"])
        acc.to_dict()["region_pref"]["regions"] = list(existing_regions)
    if update.get("score"):
        acc.seed_basics(score=update["score"])
    if update.get("subjects"):
        acc.seed_basics(subjects=update["subjects"])
    snap = acc.export_snapshot()
    # Flatten to old slot format for backwards compat
    slots = {
        "score": snap.get("score"),
        "subjects": snap.get("subjects"),
        "region_pref": snap.get("region_pref", []),
        "riasec": snap.get("riasec", {}),
        "values": snap.get("values", []),
    }
    return slots


def slots_summary(slots: dict) -> str:
    """Human-readable summary of current profile."""
    lines = []
    if slots.get("score"):
        lines.append(f"分数: {slots['score']}")
    if slots.get("subjects"):
        lines.append(f"选科: {slots['subjects']}")
    riasec = slots.get("riasec", {}) or {}
    if riasec:
        dim_names = {"R": "动手操作", "I": "研究思考", "A": "艺术创造", "S": "帮助他人", "E": "领导说服", "C": "规范有序"}
        top = sorted(riasec.items(), key=lambda x: x[1], reverse=True)[:2]
        lines.append("兴趣倾向: " + ", ".join(f"{dim_names.get(k, k)}({v})" for k, v in top))
    if slots.get("values"):
        lines.append(f"价值观: {' > '.join(slots['values'])}")
    if slots.get("region_pref"):
        lines.append(f"地域偏好: {', '.join(slots['region_pref'])}")
    return "\n".join(lines) if lines else "尚无信息"
```

- [ ] **Step 2: Run existing smoke test to verify backwards compat**

Run: `cd backend && python -c "from agents.conversation.slot_filler import merge_slots, slots_summary; r = merge_slots({}, {'riasec_update': {'I': 8}, 'values_hint': '个人成长'}); assert 'I' in r['riasec']; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/agents/conversation/slot_filler.py
git commit -m "refactor: rewrite slot_filler as EvidenceAccumulator compatibility layer"
```

---

### Task 4: Modify agent.py — Remove Old Extraction, Add Blind Spot Injection

**Files:**
- Modify: `backend/agents/conversation/agent.py`

- [ ] **Step 1: Refactor agent.py**

Changes:
1. Remove `_SLOT_PATTERN`, `_RIASEC_KW`, `_VALUES_KW`, `_REGIONS`, `_fallback_extract`, `_parse_response`
2. Remove `merge_slots`, `slots_summary` imports from slot_filler (keep slots_summary for prompt)
3. Add parameterized `build_conversation_agent(blind_spot_hints: list[str])` to inject blind spots into system prompt
4. Keep `_detect_emotion`, `_EMOTION_KW`, `_EMOTION_HINTS`

```python
# backend/agents/conversation/agent.py
"""LangGraph-based conversation agent — 1 LLM call per turn."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import settings
from agents.conversation.state import ConversationState
from agents.conversation.prompts import SYSTEM_PROMPT
from agents.conversation.slot_filler import slots_summary

llm = ChatOpenAI(model=settings.deepseek_model, api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url, temperature=0.7)

_EMOTION_KW = {
    "焦虑": ["好烦", "担心", "紧张", "不知道怎么办", "压力", "害怕", "考砸", "万一", "怎么办"],
    "迷茫": ["不知道", "随便", "都行", "没什么想法", "无所谓", "不清楚", "不太了解", "没想过"],
    "确定": ["就想学", "一定要", "必须", "确定了", "肯定是", "就是喜欢", "非它不可"],
    "烦躁": ["别问了", "不想说", "烦死了", "随便吧", "不想聊", "就这样吧"],
    "兴奋": ["特别喜欢", "超级喜欢", "太棒了", "好期待", "梦想", "真的很喜欢"],
}

_EMOTION_HINTS = {
    "焦虑": "该学生表现出焦虑情绪，请先简短安抚（1句话），再温和提问。",
    "迷茫": "该学生比较迷茫，请用具体的例子或场景来引导，避免开放式提问。",
    "确定": "该学生目标明确，可直接追问动机来源，深度挖掘为什么喜欢。",
    "烦躁": "该学生有些不耐烦，请简短回复表示理解，给对方空间，不要追问。",
    "兴奋": "该学生表现出兴奋，请鼓励ta多说，追问更多细节和感受。",
}


def _detect_emotion(user_msg: str) -> str | None:
    for emotion, keywords in _EMOTION_KW.items():
        if any(kw in user_msg for kw in keywords):
            return emotion
    return None


def _build_system_prompt(stage: str, slots_summary_text: str, blind_spot_hints: list[str], emotion: str | None) -> str:
    content = SYSTEM_PROMPT.format(stage=stage, slots_summary=slots_summary_text)
    if blind_spot_hints:
        hint_text = "、".join(blind_spot_hints)
        content += f"\n\n## 当前未探索领域\n以下维度尚无证据：{hint_text}。在后续对话中自然地引导学生谈论这些方面，避免直接提问'你喜欢动手吗'这类生硬问题。"
    if emotion:
        content += f"\n\n## 情绪提示\n{_EMOTION_HINTS.get(emotion, '')}"
    return content


async def conversation_node(state: ConversationState, blind_spot_hints: list[str] | None = None) -> dict:
    summary = slots_summary(state.get("slots", {}))
    last_user = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            last_user = m.content
            break
    emotion = _detect_emotion(last_user)
    system_content = _build_system_prompt(state["stage"].value, summary, blind_spot_hints or [], emotion)
    system = SystemMessage(content=system_content)
    msgs = [system] + state["messages"]
    response = await llm.ainvoke(msgs)
    return {"messages": [response], "slots": state.get("slots", {})}


def build_conversation_graph():
    graph = StateGraph(ConversationState)
    graph.add_node("conversation", conversation_node)
    graph.set_entry_point("conversation")
    graph.add_edge("conversation", END)
    return graph.compile(checkpointer=MemorySaver())


agent = build_conversation_graph()
```

- [ ] **Step 2: Verify imports**

Run: `cd backend && python -c "from agents.conversation.agent import agent, _detect_emotion, _build_system_prompt; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/agents/conversation/agent.py
git commit -m "refactor: simplify agent.py — remove keyword extraction, add blind spot injection"
```

---

### Task 5: Modify chat.py — Wire New Pipeline + Fix Stage Issues

**Files:**
- Modify: `backend/api/routes/chat.py`

- [ ] **Step 1: Rewrite chat.py WebSocket handler**

Key changes:
1. Replace `_determine_next_stage` with evidence-based logic
2. Call `analyze_turn` after each conversation agent response
3. Store evidence in Redis state
4. Fix confirm→done summary (send summary even when going to DONE)
5. Add `turns` counter instead of `open_turns`

```python
# backend/api/routes/chat.py
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from api.deps import get_current_user
from services.chat_service import get_dialog_state, save_dialog_state, create_session, delete_dialog_state
from agents.conversation.state import Stage, STAGE_ORDER
from agents.conversation.agent import agent as conv_agent, _build_system_prompt, _detect_emotion
from agents.conversation.slot_filler import slots_summary
from agents.conversation.profile_analyzer import analyze_turn
from agents.conversation.evidence_accumulator import EvidenceAccumulator, compute_completeness
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from config import settings

router = APIRouter()

RIASEC_KEYS = ["riasec_R", "riasec_I", "riasec_A", "riasec_S", "riasec_E", "riasec_C"]


def _determine_next_stage(evidence: dict, current_stage: Stage, turns: int) -> Stage:
    idx = STAGE_ORDER.index(current_stage)
    if idx >= len(STAGE_ORDER) - 1:
        return current_stage

    if current_stage == Stage.CONFIRM:
        return Stage.DONE

    eng = evidence.get("engagement", {})
    region_pref = evidence.get("region_pref", {}).get("regions", [])
    values_count = evidence.get("values", {}).get("evidence_count", 0)

    if current_stage == Stage.OPEN:
        if eng.get("trust_level") in ("medium", "high"):
            return Stage.EXPLORE
        if turns >= 5:
            return Stage.EXPLORE
        return Stage.OPEN

    if current_stage == Stage.EXPLORE:
        covered = sum(1 for d in RIASEC_KEYS if evidence[d]["evidence_count"] > 0)
        if covered >= 3 and region_pref:
            return Stage.FOCUS
        return Stage.EXPLORE

    if current_stage == Stage.FOCUS:
        covered = sum(1 for d in RIASEC_KEYS if evidence[d]["evidence_count"] > 0)
        if covered >= 4 and values_count >= 1:
            return Stage.CONFIRM
        return Stage.FOCUS

    return current_stage


async def _persist_profile(user_id: str, evidence: dict):
    try:
        from services.profile_service import save_profile
        from models import async_session
        acc = EvidenceAccumulator.from_dict(evidence)
        snapshot = acc.export_snapshot()
        async with async_session() as db:
            await save_profile(db, user_id, snapshot)
    except Exception:
        pass


@router.patch("/profile")
async def update_user_profile(body: dict, user: dict = Depends(get_current_user)):
    from sqlalchemy import update
    from models import async_session
    from models.user import User

    score = body.get("score", 0)
    subjects = body.get("subjects", "")
    region = body.get("region", "")

    async with async_session() as db:
        await db.execute(
            update(User).where(User.id == user["user_id"]).values(
                score=score, subjects=subjects, region=region
            )
        )
        await db.commit()
    return {"status": "ok", "score": score, "subjects": subjects, "region": region}


@router.websocket("/session/{session_id}")
async def chat_websocket(ws: WebSocket, session_id: str):
    await ws.accept()
    state_data = await get_dialog_state(session_id)
    if not state_data:
        await ws.send_json({"type": "error", "content": "Session not found"})
        await ws.close()
        return

    # Initialize evidence or migrate from old slots
    if "evidence" not in state_data:
        acc = EvidenceAccumulator()
        old_slots = state_data.get("slots", {})
        if old_slots.get("score"):
            acc.seed_basics(score=old_slots["score"])
        if old_slots.get("subjects"):
            acc.seed_basics(subjects=old_slots["subjects"])
        if old_slots.get("region_pref"):
            acc.seed_basics(region=old_slots["region_pref"])
        state_data["evidence"] = acc.to_dict()
    if "turns" not in state_data:
        state_data["turns"] = 0

    # Send initial state sync
    acc_init = EvidenceAccumulator.from_dict(state_data["evidence"])
    await ws.send_json({
        "type": "profile_update",
        "field": "slots",
        "value": acc_init.export_snapshot(),
        "confidence": 0.7,
    })
    await ws.send_json({
        "type": "stage_change",
        "from": "none",
        "to": state_data.get("stage", "open"),
    })

    session_llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            user_content = msg.get("content", "")

            await ws.send_json({"type": "thinking", "message": "正在分析你的回答..."})

            # Build message history
            history = []
            for m in state_data.get("messages", []):
                if m["role"] == "user":
                    history.append(HumanMessage(content=m["content"]))
                else:
                    history.append(AIMessage(content=m["content"]))
            history.append(HumanMessage(content=user_content))

            current_stage = Stage(state_data.get("stage", "open"))
            state_data["turns"] = state_data.get("turns", 0) + 1
            acc = EvidenceAccumulator.from_dict(state_data["evidence"])
            blind_spots = acc.detect_blind_spots()

            # Build system prompt with blind spot hints
            slots_text = slots_summary(acc.export_snapshot())
            emotion = _detect_emotion(user_content)
            system_content = _build_system_prompt(current_stage.value, slots_text, blind_spots, emotion)
            system_msg = SystemMessage(content=system_content)
            msgs = [system_msg] + history

            # Step 1: Conversation agent
            ai_response = await session_llm.ainvoke(msgs)
            ai_msg = ai_response.content

            # Step 2: Profile analyzer (analyze this turn)
            analysis = await analyze_turn(user_content, ai_msg, acc.to_dict(), blind_spots)

            # Apply new evidence
            for evt in analysis["new_evidence"]:
                acc.add_evidence(
                    dimension=evt["dimension"],
                    source_turn=state_data["turns"],
                    user_quote=evt["user_quote"],
                    inferred_score=evt["inferred_score"],
                    rationale=evt["rationale"],
                    confidence=evt["confidence"],
                )
            if analysis.get("values_hint"):
                existing_vals = acc.to_dict().get("values", {}).get("ranked", [])
                if analysis["values_hint"] not in existing_vals:
                    existing_vals.append(analysis["values_hint"])
                acc.set_values(existing_vals)
            if analysis.get("region_mentioned"):
                existing_regions = set(acc.to_dict().get("region_pref", {}).get("regions", []))
                existing_regions.add(analysis["region_mentioned"])
                acc.to_dict()["region_pref"]["regions"] = list(existing_regions)
            acc.set_engagement(**analysis.get("engagement_assessment", {}))

            # Determine stage
            next_stage = _determine_next_stage(acc.to_dict(), current_stage, state_data["turns"])
            stage_changed = next_stage != current_stage

            # Update state
            state_data["messages"].append({"role": "user", "content": user_content})
            state_data["messages"].append({"role": "assistant", "content": ai_msg})
            state_data["stage"] = next_stage.value
            state_data["evidence"] = acc.to_dict()

            await save_dialog_state(session_id, state_data)
            snapshot = acc.export_snapshot()
            await _persist_profile(state_data["user_id"], acc.to_dict())

            # Send AI response
            await ws.send_json({
                "type": "message",
                "role": "assistant",
                "content": ai_msg,
                "stage": next_stage.value,
            })

            # Profile update (always, keeps sidebar in sync)
            await ws.send_json({
                "type": "profile_update",
                "field": "slots",
                "value": snapshot,
                "confidence": 0.7,
            })

            # Stage transition handling
            if stage_changed:
                await ws.send_json({
                    "type": "stage_change",
                    "from": current_stage.value,
                    "to": next_stage.value,
                })
                # Send summary for the stage just completed (including confirm→done)
                summary_text = slots_summary(snapshot)
                await ws.send_json({
                    "type": "summary",
                    "stage": current_stage.value,
                    "content": summary_text,
                    "profile_snapshot": snapshot,
                })

            if next_stage == Stage.DONE:
                await ws.send_json({
                    "type": "stage_change",
                    "from": current_stage.value,
                    "to": "done",
                })
                # Invalidate recommendation cache
                try:
                    import redis.asyncio as aioredis
                    from config import settings
                    r = aioredis.from_url(settings.redis_url)
                    await r.delete(f"recs_cache:{state_data['user_id']}")
                except Exception:
                    pass

    except WebSocketDisconnect:
        pass


@router.post("/session")
async def new_session(user: dict = Depends(get_current_user)):
    from sqlalchemy import select
    from models import async_session
    from models.user import User

    acc = EvidenceAccumulator()
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user["user_id"]))
        u = result.scalar_one_or_none()
        if u:
            if u.score:
                acc.seed_basics(score=u.score)
            if u.subjects:
                acc.seed_basics(subjects=u.subjects)
            if u.region:
                acc.seed_basics(region=[u.region])

    initial_slots = acc.export_snapshot()
    sid = await create_session(user["user_id"], initial_slots)
    # Also store evidence in session state
    state = await get_dialog_state(sid)
    if state:
        state["evidence"] = acc.to_dict()
        await save_dialog_state(sid, state)
    return {"session_id": sid}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    state = await get_dialog_state(session_id)
    if not state:
        return {"error": "not found"}
    return {
        "session_id": session_id,
        "stage": state.get("stage"),
        "slots": EvidenceAccumulator.from_dict(state.get("evidence", {})).export_snapshot() if state.get("evidence") else state.get("slots"),
        "messages": state.get("messages", []),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    await delete_dialog_state(session_id)
    return {"status": "deleted"}
```

- [ ] **Step 2: Verify import chain**

Run: `cd backend && python -c "from api.routes.chat import _determine_next_stage, router; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/api/routes/chat.py
git commit -m "feat: wire profile analyzer into chat — evidence-based staging, fix confirm summary, cache invalidation"
```

---

### Task 6: Adaptive Recommendation Prompt (L1-L4)

**Files:**
- Modify: `backend/services/recommendation_service.py`

- [ ] **Step 1: Add completeness-aware RANKING_PROMPT**

```python
# In recommendation_service.py, add after the existing RANKING_PROMPT:

L1_PROMPT_ADDON = """
## 匹配策略（基础推荐）
学生画像信息有限（仅分数+选科）。请主要依据位次匹配进行排序。
在理由中建议学生继续对话以获取更精准的推荐。
"""

L2_PROMPT_ADDON = """
## 匹配策略（较完整推荐）
学生画像包含：分数+选科+地域偏好+部分兴趣倾向。
权重分配：60% 位次匹配 + 25% 兴趣倾向 + 15% 地域偏好。
"""

L3_PROMPT_ADDON = """
## 匹配策略（深度个性化推荐）
学生画像包含：分数+选科+地域偏好+深度兴趣倾向+价值观排序。
权重分配：40% 位次匹配 + 35% 兴趣倾向 + 15% 价值观 + 10% 地域偏好。
"""

def _get_adaptive_prompt(profile: dict) -> str:
    completeness = profile.get("completeness", "L1")
    if completeness == "L3":
        return RANKING_PROMPT + L3_PROMPT_ADDON
    elif completeness == "L2":
        return RANKING_PROMPT + L2_PROMPT_ADDON
    return RANKING_PROMPT + L1_PROMPT_ADDON

# In generate_recommendations, replace RANKING_PROMPT usage with _get_adaptive_prompt:
# OLD: prompt = RANKING_PROMPT.format(profile=profile_text, candidates=candidate_text)
# NEW: prompt_template = _get_adaptive_prompt(profile)
#      prompt = prompt_template.format(profile=profile_text, candidates=candidate_text)
```

- [ ] **Step 2: Verify**

Run: `cd backend && python -c "from services.recommendation_service import _get_adaptive_prompt; p=_get_adaptive_prompt({'completeness':'L2'}); assert '60%' in p; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/services/recommendation_service.py
git commit -m "feat: adaptive recommendation prompt based on profile completeness L1-L4"
```

---

### Task 7: Frontend Types + EvidenceProgress Component

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/components/chat/EvidenceProgress.tsx`
- Modify: `frontend/src/pages/Chat.tsx` (swap import)

- [ ] **Step 1: Add types**

```typescript
// frontend/src/types/index.ts — add after existing types:

export interface EvidenceItem {
  id: string
  dimension: string
  source_turn: number
  user_quote: string
  inferred_value: {
    dimension: string
    score: number
    rationale: string
  }
  confidence: number
}

export interface DimensionState {
  dimension: string
  label: string
  score?: number
  evidence_count: number
  confidence: number
  evidence?: EvidenceItem[]
}

// Update ProfileSlot to match new snapshot format
export interface ProfileSlot {
  score?: number
  subjects?: string
  riasec?: Record<string, number>
  values?: string[]
  region_pref?: string[]
  completeness?: string   // L1/L2/L3/L4
  engagement?: {
    trust_level: string
    willingness_to_share: number
    indicators: string[]
  }
}
```

- [ ] **Step 2: Create EvidenceProgress component**

```tsx
// frontend/src/components/chat/EvidenceProgress.tsx
import type { ProfileSlot } from '../../types'

const RIASEC_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  R: { label: '动手操作', color: '#1E40AF', bg: '#DBEAFE' },
  I: { label: '研究思考', color: '#065F46', bg: '#D1FAE5' },
  A: { label: '艺术创造', color: '#6D28D9', bg: '#EDE9FE' },
  S: { label: '帮助他人', color: '#92400E', bg: '#FEF3C7' },
  E: { label: '领导说服', color: '#BE185D', bg: '#FCE7F3' },
  C: { label: '规范有序', color: '#0369A1', bg: '#E0F2FE' },
}

function getCompletenessLabel(level?: string) {
  switch (level) {
    case 'L4': return { text: '已确认', color: '#065F46', bg: '#D1FAE5' }
    case 'L3': return { text: '深度画像', color: '#6D28D9', bg: '#EDE9FE' }
    case 'L2': return { text: '较完整', color: '#92400E', bg: '#FEF3C7' }
    default: return { text: '基础画像', color: '#64748B', bg: '#F1F5F9' }
  }
}

export default function EvidenceProgress({ slots }: { slots: ProfileSlot }) {
  const riasec = slots.riasec || {}
  const dims = ['R', 'I', 'A', 'S', 'E', 'C']
  const covered = dims.filter(d => riasec[d] !== undefined).length
  const pct = Math.round((covered / 6) * 100)
  const cLevel = getCompletenessLabel(slots.completeness)

  return (
    <div>
      <div className="text-xs uppercase text-muted tracking-wider mb-2">已收集信息</div>

      {/* Basics */}
      <div className="space-y-1 mb-3">
        <div className={`flex items-center gap-2 text-xs ${slots.score ? '' : 'opacity-40'}`}>
          <span className={slots.score ? 'text-success' : ''}>{slots.score ? '✓' : '○'}</span>
          <span>分数 / 选科</span>
        </div>
        <div className={`flex items-center gap-2 text-xs ${(slots.region_pref || []).length > 0 ? '' : 'opacity-40'}`}>
          <span className={(slots.region_pref || []).length > 0 ? 'text-success' : ''}>{(slots.region_pref || []).length > 0 ? '✓' : '○'}</span>
          <span>地域偏好</span>
        </div>
      </div>

      {/* RIASEC hex grid */}
      <div className="text-xs text-muted mb-1.5">RIASEC 兴趣倾向</div>
      <div className="grid grid-cols-3 gap-1 mb-3">
        {dims.map(d => {
          const info = RIASEC_LABELS[d]
          const score = riasec[d]
          const done = score !== undefined
          return (
            <div key={d} className={`rounded-lg p-1.5 text-center border transition-all ${done ? 'border-current' : 'border-border opacity-40'}`} style={done ? { borderColor: info.color, background: info.bg } : {}}>
              <div className="text-xs font-bold" style={done ? { color: info.color } : {}}>{d}</div>
              <div className="text-[9px] text-muted leading-tight">{info.label}</div>
              {done && <div className="text-[10px] font-bold mt-0.5" style={{ color: info.color }}>{score}</div>}
            </div>
          )
        })}
      </div>

      {/* Values */}
      <div className={`flex items-center gap-2 text-xs mb-3 ${(slots.values || []).length > 0 ? '' : 'opacity-40'}`}>
        <span className={(slots.values || []).length > 0 ? 'text-success' : ''}>{(slots.values || []).length > 0 ? '✓' : '○'}</span>
        <span>价值观排序 ({slots.values?.length || 0}/2)</span>
      </div>

      {/* Completeness badge */}
      <div className="flex items-center justify-between">
        <span className="text-xs px-2 py-0.5 rounded-full font-semibold" style={{ color: cLevel.color, background: cLevel.bg }}>{cLevel.text}</span>
        <span className="text-xs text-muted">{covered}/6 维度</span>
      </div>

      {/* Progress bar */}
      <div className="mt-2 bg-border rounded h-1">
        <div className="bg-primary h-1 rounded transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-muted mt-1 text-right">完成度 {pct}%</div>
    </div>
  )
}
```

- [ ] **Step 3: Update Chat.tsx import**

In `frontend/src/pages/Chat.tsx`, change:
```tsx
import SlotProgress from '../components/chat/SlotProgress'
// to:
import EvidenceProgress from '../components/chat/EvidenceProgress'
```

And change `<SlotProgress slots={slots} />` to `<EvidenceProgress slots={slots} />`.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No new type errors from EvidenceProgress

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/components/chat/EvidenceProgress.tsx frontend/src/pages/Chat.tsx
git commit -m "feat: replace SlotProgress with EvidenceProgress — RIASEC hex grid + completeness badge"
```

---

### Task 8: SummaryModal + ProfileSummaryBar Updates

**Files:**
- Modify: `frontend/src/components/chat/SummaryModal.tsx`
- Modify: `frontend/src/components/recommendation/ProfileSummaryBar.tsx`

- [ ] **Step 1: Update SummaryModal to show evidence details**

In `SummaryModal.tsx`, replace the generic profile display with evidence items:

```tsx
// Key change: show RIASEC dimensions with scores from profile_snapshot
{profile.riasec && Object.keys(profile.riasec).length > 0 && (
  <div className="mt-3">
    <div className="text-xs font-semibold text-muted mb-2">兴趣倾向 (RIASEC)</div>
    <div className="grid grid-cols-3 gap-2">
      {Object.entries(profile.riasec as Record<string, number>).map(([dim, score]) => (
        <div key={dim} className="bg-gray-50 rounded-lg p-2 text-center">
          <div className="text-sm font-bold">{dim}</div>
          <div className="text-lg font-bold text-primary">{score}</div>
        </div>
      ))}
    </div>
  </div>
)}
{/* Show completeness level */}
{profile.completeness && (
  <div className="mt-2 text-xs text-muted">
    画像完整度：<span className="font-bold">{profile.completeness}</span>
  </div>
)}
```

- [ ] **Step 2: Update ProfileSummaryBar to show L1-L4 badge**

```tsx
// Add completeness badge next to profile tags:
{profile.completeness && (
  <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-semibold ${
    profile.completeness === 'L3' ? 'bg-purple-100 text-purple-700' :
    profile.completeness === 'L2' ? 'bg-amber-100 text-amber-700' :
    'bg-gray-100 text-gray-600'
  }`}>
    {profile.completeness === 'L3' ? '深度画像' :
     profile.completeness === 'L2' ? '较完整' : '基础画像'}
  </span>
)}
{/* Show "return to chat" prompt for L1/L2 */}
{(profile.completeness === 'L1' || profile.completeness === 'L2') && (
  <div className="text-xs text-blue-500 mt-1">
    继续对话完善画像，获取更精准的推荐 →
  </div>
)}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -10`
Expected: No new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/SummaryModal.tsx frontend/src/components/recommendation/ProfileSummaryBar.tsx
git commit -m "feat: show evidence details in summary modal, L1-L4 badge in profile bar"
```

---

## Execution Order

Tasks 1→2→3→4→5 must be sequential (each builds on the previous).  
Tasks 6 and 7 can run in parallel with Tasks 1-5.  
Task 8 depends on Task 7.

```
  1 → 2 → 3 → 4 → 5
                    ↘
                      6 → [parallel]
                    ↗
  7 → 8
```
