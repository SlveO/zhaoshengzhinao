# 用户画像构建系统重设计

> 日期：2026-05-14 | 状态：设计中

## 背景

当前画像构建方案存在以下问题：
1. 基于关键词匹配提取 RIASEC/价值观不可靠
2. LLM 输出的 `<!--SLOTS-->` JSON 块经常不产生或格式错误
3. 阶段推进只看 slot 数量不看对话质量
4. RIASEC 评分用简单关键词命中计数+平均

## 目标

重新设计一套可靠的画像构建系统，平衡精确性、自然性和速度。

---

## 1. 总体架构：双轨并行 + 盲区引导

```
┌─────────────────────────────────────────────────────┐
│                    用户对话界面                      │
│  ┌──────────┐  ┌──────────────────────────────────┐ │
│  │ 侧边栏    │  │  对话区                           │ │
│  │ 阶段指示  │  │  自然对话流                       │ │
│  │ 证据进度  │  │                                  │ │
│  │ 置信度环  │  │  阶段小结弹窗（证据阈值触发）       │ │
│  └──────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
         ▲                              │
         │         WebSocket            │
         ▼                              ▼
┌─────────────────────────────────────────────────────┐
│                   Chat Route (chat.py)               │
│                                                     │
│  ┌──────────────┐    ┌─────────────────────────┐    │
│  │ 对话 Agent    │    │ 画像分析器 Agent          │    │
│  │ (自然对话)    │───▶│ (每次对话后分析)          │    │
│  └──────────────┘    └───────────┬─────────────┘    │
│                                  │                   │
│         ┌────────────────────────┘                   │
│         ▼                                           │
│  ┌─────────────────────────────────────────────┐    │
│  │ 证据累积器 (evidence_accumulator.py)          │    │
│  │  - 维度证据条目存储                           │    │
│  │  - 置信度计算                                │    │
│  │  - 盲区检测                                  │    │
│  │  - 画像摘要生成                              │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

两条并行轨道：
- **对话轨道**：对话 Agent 接收盲区提示 → 自然引导对话 → 覆盖未探索维度
- **分析轨道**：画像分析器分析每轮对话 → 提取证据条目 → 累积证据 → 检测盲区

---

## 2. 证据模型

每个画像维度不直接存"分数"，而是存**证据条目列表**。每条证据来自用户对话中的具体表达。

### 证据条目结构

```python
EvidenceItem = {
    "id": "evt_001",
    "dimension": "riasec_I",        # 维度标识
    "source_turn": 3,               # 第几轮对话产生的
    "user_quote": "我特别喜欢自己查资料研究不明白的东西",  # 用户原话
    "inferred_value": {             # 分析器推断的值
        "dimension": "I",
        "score": 8,
        "rationale": "学生表达了对独立研究的明确兴趣"
    },
    "confidence": 0.6,              # 本条证据自身的置信度
    "created_at": "2026-05-14T..."
}
```

### 维度状态（由证据累积器计算）

```python
DimensionState = {
    "dimension": "riasec_I",
    "label": "研究思考",
    "score": 8.0,                   # 基于所有证据的加权分
    "evidence_count": 2,
    "confidence": 0.78,             # 聚合置信度
    "last_updated_turn": 5,
}
```

### 维度定义

| 类别 | 维度 | 最少证据数 | 说明 |
|------|------|-----------|------|
| 基础 | score (分数) | 1 | 来自 WelcomeModal，置信度 1.0 |
| 基础 | subjects (选科) | 1 | 来自 WelcomeModal，置信度 1.0 |
| 基础 | region_pref (地域) | 1 | WelcomeModal 或对话中提到 |
| RIASEC | R 动手操作 | 1 | 实验/制作/修理/工具操作 |
| RIASEC | I 研究思考 | 1 | 分析/探索/理论/逻辑推理 |
| RIASEC | A 艺术创造 | 1 | 设计/创作/表达/想象 |
| RIASEC | S 帮助他人 | 1 | 助人/教育/沟通/团队合作 |
| RIASEC | E 领导说服 | 1 | 管理/组织/说服/竞争 |
| RIASEC | C 规范有序 | 1 | 整理/数据处理/规则/条理 |
| 价值观 | values | 2 | 社会贡献/个人成长/工作稳定/薪资水平 |
| 其他 | career_vision | 1 | 职业憧憬 |
| 其他 | family_influence | 1 | 家庭影响程度 |
| 扩展 | learning_style | 1 | 学习风格偏好 |
| 扩展 | work_env_pref | 1 | 工作环境偏好 |

### RIASEC 评分方法：B+C 混合

- **B 证据累积+置信度**（基础框架）：每维度累积证据条目，置信度随证据量增长。1条清晰证据=可评分(0.5)，2条以上=较可靠(0.7-0.9)
- **C 对比锚定**（focus 阶段加速）：对盲区维度使用隐含对比选择快速确定排序

### 证据存储

证据条目存储在 Redis 中（与当前对话状态共享同一个 Redis key），序列化为 JSON：

```python
# Redis key: dialog:{session_id}
# 结构：{
#   "messages": [...],
#   "stage": "explore",
#   "evidence": {
#       "score": {"value": 620, "evidence_count": 1, "confidence": 1.0},
#       "riasec_R": {"value": None, "evidence": [], "evidence_count": 0, "confidence": 0},
#       "riasec_I": {"value": 8.0, "evidence": [{...}], "evidence_count": 2, "confidence": 0.78},
#       ...
#   },
#   "engagement": {"trust_level": "medium", ...}
# }
```

_每次对话回合结束后，通过 `_persist_profile()` 将画像快照同时写入 PostgreSQL user_profiles 表。_

### 画像完整度计算

```python
def compute_completeness(evidence: dict) -> str:
    """L1(基础) / L2(较完整) / L3(深度) / L4(已确认)"""
    riasec_covered = sum(1 for d in RIASEC_KEYS if evidence[d]["evidence_count"] > 0)
    has_values = evidence["values"]["evidence_count"] >= 1
    
    if riasec_covered >= 4 and has_values:
        return "L3"
    elif riasec_covered >= 2 and evidence.get("region_pref"):
        return "L2"
    else:
        return "L1"
    # L4 is set when user explicitly confirms the profile in confirm stage
```

---

## 3. 画像分析器 Agent & 盲区引导

### 画像分析器（独立 Agent，每轮对话后调用）

```
输入：本轮用户消息 + AI 回复 + 已有证据摘要
输出：新增证据条目列表 + JSON 结构化输出
```

关键设计：
- 使用 **structured output**（JSON schema 约束），不再依赖正则匹配 `<!--SLOTS-->`
- 只输出**本轮新增**的证据，不重复已有条目
- 找不到新证据就返回空列表（不强行编造）

### 盲区检测（在证据累积器中计算）

```python
def detect_blind_spots(dimensions: dict) -> list[str]:
    hints = []
    for dim in RIASEC_DIMS:
        if dim.evidence_count == 0:
            hints.append(f"尚未了解学生的{dim.label}倾向({dim.key})")
    return hints
```

盲区提示注入到对话 Agent 的 system prompt 中，形式为：
> "当前尚未探索的领域：动手操作(R)、领导说服(E)。在后续对话中自然地引导学生谈论这些方面。"

### 文件对应关系

- 新建 `backend/agents/conversation/profile_analyzer.py` — 画像分析器
- 新建 `backend/agents/conversation/evidence_accumulator.py` — 证据累积器
- 替换 `backend/agents/conversation/slot_filler.py` — 移除旧逻辑
- 修改 `backend/agents/conversation/agent.py` — 移除 `_SLOT_PATTERN` 和 `_fallback_extract`

---

## 4. 增量更新与推荐触发

### 核心变化：阶段驱动 → 证据驱动

阶段仍然是导航框架，但触发小结和推荐的时机由**证据量**决定。

### 推荐可用性分级

```
证据量          →  推荐质量        →  前端标识
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
仅分数+选科     →  仅按位次匹配     "基础推荐 — 继续对话可获得更精准推荐"
+地域+2 RIASEC  →  位次+兴趣+地域   "较完整推荐"
+价值观+4+RIASEC →  全面匹配        "深度个性化推荐"
用户确认后画像  →  最终推荐         "已确认画像"
```

### 关键规则

- "跳过对话"按钮**随时可用**，无论画像多寡
- 推荐页根据画像完整度显示质量标识
- 用户返回对话继续聊天后，画像增量更新，推荐可刷新

### 小结弹窗触发 — A+B 结合

- **A**：每阶段结束仍弹小结，但推进条件从"slot 数量"改为"证据量+置信度达标"
- **B**：侧边栏持续显示画像构建进度（证据条数+置信度环）

---

## 5. 阶段推进逻辑（证据驱动）

不再用 `_determine_next_stage()` 检查 slot 数量，改为检查证据累积状态。

### OPEN → EXPLORE：参与度判断

画像分析器每轮输出参与度评估：

```python
# 分析器输出中增加
{
    "engagement_assessment": {
        "trust_level": "medium",        # low / medium / high
        "willingness_to_share": 0.7,    # 0-1
        "indicators": [
            "学生主动分享了个人经历",
            "学生回答了开放式问题并给出了具体细节",
            "学生表达了真实情感（非敷衍回应）"
        ]
    }
}
```

推进条件：
```python
if current_stage == Stage.OPEN:
    eng = evidence.get("engagement", {})
    if eng.get("trust_level") in ("medium", "high"):
        return Stage.EXPLORE
    # 最多 5 轮兜底，防止无限停留
    if turns >= 5:
        return Stage.EXPLORE
```

### EXPLORE → FOCUS：RIASEC 覆盖度

```python
if current_stage == Stage.EXPLORE:
    riasec_dims = ["riasec_R","riasec_I","riasec_A","riasec_S","riasec_E","riasec_C"]
    covered = sum(1 for d in riasec_dims if evidence[d]["evidence_count"] > 0)
    if covered >= 3 and evidence.get("region_pref"):
        return Stage.FOCUS
```

### FOCUS → CONFIRM：RIASEC 覆盖 + 价值观

focus 阶段使用**对比锚定**加速盲区维度覆盖：
- Agent 对证据为空的 RIASEC 维度，使用隐含对比提问（"如果必须在 A 和 B 之间..."）
- 1-2 轮对比即可覆盖剩余盲区

```python
if current_stage == Stage.FOCUS:
    covered = sum(1 for d in riasec_dims if evidence[d]["evidence_count"] > 0)
    if covered >= 4 and evidence.get("values", {}).get("evidence_count", 0) >= 1:
        return Stage.CONFIRM
```

### CONFIRM → DONE：用户确认

```python
if current_stage == Stage.CONFIRM:
    return Stage.DONE  # 用户确认后即完成
```

---

## 6. 单轮对话数据流

```
用户发送消息
      │
      ▼
┌─────────────────┐
│ 1. thinking 消息  │  → 前端显示"正在分析..."
└─────────────────┘
      │
      ▼
┌─────────────────────────────┐
│ 2. 对话 Agent (agent.py)     │
│    - system prompt 含盲区提示  │
│    - 生成自然对话回复          │
└─────────────────────────────┘
      │
      ▼
┌─────────────────────────────┐
│ 3. 画像分析器                  │
│    (profile_analyzer.py)     │
│    - 输入：用户消息+AI回复     │
│    - 输出：新证据条目(0-N条)   │
│    - 输出：参与度评估          │
│    - structured output 保证   │
│      JSON 格式正确            │
└─────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│ 4. 证据累积器                  │
│    (evidence_accumulator.py)  │
│    - 追加新证据到各维度         │
│    - 重新计算置信度             │
│    - 检测盲区                  │
│    - 判断阶段是否推进           │
└──────────────────────────────┘
      │
      ▼
┌──────────────────────────────┐
│ 5. WebSocket 发送（可能多条）   │
│    - AI 回复 (message)        │
│    - 画像更新 (profile_update) │
│    - 阶段变更 (stage_change)   │
│    - 小结弹窗 (summary) 若推进  │
└──────────────────────────────┘
```

步骤 2 → 3 顺序执行：画像分析器需要对话 Agent 的回复作为输入。每轮增量延迟预计 2-5 秒（两次 LLM 调用）。

---

## 7. 与推荐系统联动

### Profile Snapshot 生成

证据累积器从当前证据状态生成 profile snapshot：

```python
def build_profile_snapshot(evidence: dict) -> dict:
    return {
        "score": evidence["score"]["value"],
        "subjects": evidence["subjects"]["value"],
        "region_pref": evidence["region_pref"]["regions"],
        "riasec": {dim: state["score"] for dim, state in evidence["riasec"].items()},
        "values": evidence["values"]["ranked"],
        "completeness": compute_completeness(evidence),  # L1/L2/L3/L4
    }
```

### 自适应推荐 Prompt

RANKING_PROMPT 根据画像完整度调整匹配策略：

| 等级 | 可用维度 | 匹配权重 |
|------|---------|---------|
| L1 | 仅分数+选科 | 100% 位次匹配 |
| L2 | +地域+≤3 RIASEC | 60% 位次 + 25% 兴趣 + 15% 地域 |
| L3 | +≥4 RIASEC+价值观 | 40% 位次 + 35% 兴趣 + 15% 价值观 + 10% 地域 |
| L4 | 用户确认后 | 同 L3 + 标注"画像已确认" |

### 增量推荐刷新

- 每次证据变更 → 清除 Redis 推荐缓存 (`recs_cache:{user_id}`)
- 用户再进推荐页 → 自动用最新画像重新生成

---

## 8. 错误处理

```
画像分析器异常
  ├── LLM 返回格式错误 → 跳过本轮分析，保留旧证据，不阻断对话
  ├── LLM 超时 (>5s)  → 跳过本轮分析，下次对话一起分析
  ├── structured output 为空 → 视为本轮无新证据
  └── 连续 3 轮分析失败 → 降级为关键词回退

证据累积器异常
  ├── JSON 序列化失败 → 使用 dict 副本，不污染原状态
  └── Redis 写入失败 → 对话不依赖 Redis（仅缓存），继续

推荐系统
  ├── 画像为空 → 仅用 user 表数据（分数+选科+地域）
  ├── 候选检索空 → 返回空列表 + "暂无匹配院校"提示
  └── LLM 超时 → 返回原始检索结果不带 LLM 排序
```

核心原则：**分析层失败不阻断对话层。**

---

## 9. 前端变更

### 侧边栏 SlotProgress → EvidenceProgress

```
当前：分数/选科 ✓ | 地域偏好 ✓ | 兴趣倾向 ○ | 价值观排序 ○ | 完成度 X%
改为：分数/选科 ✓ | 地域偏好 ✓ | 
      RIASEC  R ○ I ✓ A ○ S ✓ E ○ C ○  (3/6)
      价值观 ○ (0/2) | 完成度 L2
```

### 阶段小结弹窗

- 触发时机不变（阶段推进时弹出）
- 内容从 `slots_summary()` 改为显示证据详情（每条证据的用户原话 + 推断值）
- confirm 阶段的小结显示完整画像，用户可以修正

### 推荐页 ProfileSummaryBar

- 增加画像完整度标记（L1-L4 标签）
- L1/L2 时显示"继续完善画像 → 返回对话"引导

---

## 10. 涉及文件清单

| 操作 | 文件 | 说明 |
|------|------|------|
| **新建** | `backend/agents/conversation/profile_analyzer.py` | 画像分析器 Agent，structured output |
| **新建** | `backend/agents/conversation/evidence_accumulator.py` | 证据累积器，置信度/盲区/摘要 |
| **重写** | `backend/agents/conversation/slot_filler.py` | 改为兼容旧接口的薄封装，转发到新系统 |
| **修改** | `backend/agents/conversation/agent.py` | 移除 `_SLOT_PATTERN`、`_fallback_extract`；集成分析器+累积器 |
| **修改** | `backend/api/routes/chat.py` | 新 `_determine_next_stage()`；并行调用对话Agent+分析器；移除旧 summary 逻辑 |
| **修改** | `backend/services/recommendation_service.py` | 自适应 prompt（L1-L4 匹配权重） |
| **修改** | `backend/api/routes/recommendation.py` | 证据变更时清除缓存；profile snapshot 生成 |
| **修改** | `frontend/src/components/chat/SlotProgress.tsx` | 改为 EvidenceProgress，显示 RIASEC 六维 + 置信度环 |
| **修改** | `frontend/src/components/chat/SummaryModal.tsx` | 显示证据详情（用户原话） |
| **修改** | `frontend/src/components/recommendation/ProfileSummaryBar.tsx` | 增加 L1-L4 完整度标签 |
| **修改** | `frontend/src/types/index.ts` | 新增 EvidenceItem、DimensionState 类型 |
