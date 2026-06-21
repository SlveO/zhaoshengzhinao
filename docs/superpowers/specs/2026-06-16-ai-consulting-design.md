# Module B: AI 咨询体系 设计文档

> 日期：2026-06-16 | 执行计划：`docs/EXECUTION_PLAN.md`

---

## 1. 概述

Module B 负责将 C-end（学生端）对话数据通过 LLM 提取为结构化学生画像，写入 `session_profiles` 表供分析看板消费，并建立准确度测试框架确保提取质量。

**核心交付：**
- B1：C-end 数据链路打通（LLM 提取 → session_profiles → 分析看板）
- B2：准确度测试框架（ground truth 数据集 + 评测脚本 + CI 集成）
- B3：交互体验优化（Phase 2，本文仅概述）

---

## 2. 架构方案：最小改动方案

在现有 C-end SSE 流程上做最小侵入式升级，复用 B2B 已验证的 LLM 提取模式但保持独立。

**核心原则：**
- 新建文件独立，不修改 B2B 的 `profile_analyzer.py` / `evidence_accumulator.py`
- 仅修改 `miniapp.py` 的 SSE 响应后阶段，不改变前端协议
- 双写策略：DB + JSON 文件同步，开发阶段可快速验证

---

## 3. Section 1：整体数据流

```
Mini-app (Vue)
  │  POST /api/v1/chat/messages (SSE)
  ▼
miniapp.py (SSE handler)
  │  1. 保存用户消息 → ChatMessage
  │  2. RAG 检索 → ChromaDB
  │  3. 构建 system prompt（注入心理引导：渐进式提问策略）
  │  4. LLM 流式生成 + SSE push
  │  5. 保存助手回复 → ChatMessage
  │  6. [NEW] 每 3 轮对话 → 触发 profile_bridge
  ▼
profile_bridge.py (新建桥接层)
  │  1. 读取 consult_sessions 基础字段
  │  2. 加载完整对话历史
  │  3. 调用 cend_profile_analyzer LLM 提取
  │  4. 更新 consult_sessions 列（province/score/等）
  │  5. Merge 写入 session_profiles.profile_json
  │  6. 同步写 JSON 到 data/extracted_profiles/{session_id}.json
  ▼
session_profiles 表
  │  被分析看板消费
  ▼
profile_dashboard / region_distribution / competitive_analysis / topic_cloud
```

**关键决策：**
- 触发时机：每 3 轮对话（`len(messages) % 3 == 0` 且有新用户消息）
- 提取字段：按 EXECUTION_PLAN 规定的 7 个层级
- 双写策略：DB + JSON 文件同步
- 错误处理：提取失败不阻塞 SSE 响应，静默 catch + logger.error

---

## 4. Section 2：cend_profile_analyzer.py

**文件：** `backend/services/cend_profile_analyzer.py`（新建）

复用 `profile_analyzer.py` 的 LLM 调用 + JSON 解析模式，使用独立 C-end 字段 prompt。

### 核心函数

```python
async def analyze_cend_turn(
    user_msg: str,
    ai_reply: str,
    existing_profile: dict,    # 当前已提取的 profile（增量模式）
    conversation_history: list  # 最近对话上下文
) -> CendExtractionResult:
    """
    返回提取结果:
    - basic: {province, subject_type, score}
    - interests: {preferred_subjects, strong_subjects, hobbies}
    - concerns: list[str]  自由标签
    - riasec: {R, I, A, S, E, C}
    - values: list[str]
    - region_pref: {province, city}
    - extra: dict
    - completeness: L1/L2/L3
    """
```

### Prompt 设计原则

- 独立 C-end system prompt（学生视角）
- 渐进式提取：优先基础信息 → 兴趣关注 → 深层 RIASEC/价值观
- 要求 LLM 仅提取**本轮新出现**的信息（增量模式），引用对话原文
- JSON 严格输出格式，复用 `parse_analysis_response()` 的 markdown 清理逻辑

### 字段提取优先级

| 优先级 | 字段 | 提取条件 |
|--------|------|----------|
| P0 | province, subject_type, score | 首轮即可提取 |
| P1 | preferred_subjects, concern_dimensions | 对话中自然提及 |
| P2 | RIASEC, values_ranking, region_pref | 需多轮积累证据 |

---

## 5. Section 3：profile_bridge.py

**文件：** `backend/services/profile_bridge.py`（新建）

### 核心函数

```python
async def bridge_profile_to_session_profiles(
    session: ConsultSession,
    extraction: CendExtractionResult,
    tenant_id: UUID
) -> None:
    """1. 更新 consult_sessions 表字段 2. Merge session_profiles 3. JSON 文件"""

async def should_extract(session: ConsultSession, db_session) -> bool:
    """消息数 % 3 == 0 且有新用户消息 → True"""
```

### session_profiles.profile_json 结构

```json
{
  "basic": {"province": "", "subject_type": "", "score": 0},
  "interests": {"preferred_subjects": [], "strong_subjects": [], "hobbies": []},
  "concerns": ["自由标签1", "自由标签2"],
  "riasec": {"R": 5, "I": 7, "A": 3, "S": 6, "E": 4, "C": 8},
  "values": ["就业前景", "学术氛围"],
  "region_pref": {"province": "", "city": ""},
  "extra": {}
}
```

### Merge 策略

- 首次提取 → INSERT 新 SessionProfile 行
- 后续提取 → UPDATE profile_json（深度 merge：新字段覆盖旧字段，列表合并去重）
- completeness 计算：>=4 RIASEC + values → L3，>=2 RIASEC + region → L2，否则 L1

### JSON 文件

- 路径：`data/extracted_profiles/{session_id}.json`
- 每次提取覆盖写入最新快照
- 目录加入 `.gitignore`

### 错误处理

- 所有操作包裹 try/except，失败时 logger.error
- 写入 analytics event 记录失败
- 不抛异常阻塞 SSE 响应流

### 心理引导 prompt（Phase 1 基础版）

在 C-end system prompt 中注入渐进式提问策略（后续 Phase 2 B3 深化）：

- **阶段 1（open）**：自然寒暄，引导透露省份/科类/分数
- **阶段 2（explore）**：基于已知信息，自然过渡到兴趣和专业偏好探索
- **阶段 3（focus）**：聚焦 2-3 个方向深入讨论，挖掘 RIASEC 维度
- **原则**：避免审讯式连续提问，每轮最多 1-2 个问题，自然回显确认关键信息

### 旧 extract_profile_from_message() 处理

`backend/services/consult_service.py` 中的旧正则 `extract_profile_from_message()` **保留不动**，但不再作为主要提取路径：

- `cend_profile_analyzer.py` 成为 C-end 提取的主路径
- 旧正则函数保留在 consult_service.py 中，作为 fallback（当 LLM 调用失败时使用）
- `miniapp.py` 中调用逻辑：先尝试 LLM 提取 → 失败时 fallback 到旧正则提取
- 后续评估如果正则 fallback 从未触发，可在 Phase 2 删除

---

## 6. Section 4：B2 准确度测试框架

### 6.1 Ground Truth 数据集

**文件 1：** `tests/benchmarks/knowledge_qa.json`（目标 >= 100 对）

```json
[
  {
    "id": "kqa_001",
    "question": "华南师范大学计算机专业2025年录取分数线是多少？",
    "expected_answer": "...",
    "source_doc": "data/approved/scnu_admission_2025.json",
    "category": "admission_score"
  }
]
```

类别：`admission_score` / `curriculum` / `employment` / `campus_life`

**文件 2：** `tests/benchmarks/profile_extraction.json`（目标 >= 50 对）

```json
[
  {
    "id": "pe_001",
    "conversation": [
      {"role": "user", "content": "你好，我是广东的高考生，学物理的"},
      {"role": "assistant", "content": "你好！..."}
    ],
    "expected_extraction": {
      "basic": {"province": "广东", "subject_type": "物理类", "score": 600},
      "interests": {"preferred_subjects": ["计算机"], "strong_subjects": [], "hobbies": []},
      "concerns": [],
      "riasec": {"R": null, "I": null, "A": null, "S": null, "E": null, "C": null},
      "values": [],
      "region_pref": {"province": null, "city": null},
      "extra": {}
    }
  }
]
```

### 6.2 评测脚本

**文件：** `tests/benchmarks/run_accuracy.py`

```
用法: python backend/tests/benchmarks/run_accuracy.py [--kb-only|--extract-only] [--output report.json]

评测维度：
  1. KB 正确性 → LLM-as-judge 评分 1-5，4+ = 正确
  2. 提取准确度 → 逐字段对比，按类型加权：
     - 基础信息 40%（province/subject_type/score 精确匹配）
     - RIASEC 30%（各维度差值 <= 2 视为正确）
     - 兴趣/关注/其他 30%（列表 Jaccard >= 0.7 视为正确）
  3. 回复速度 → SSE first-token / full-reply / P50 P95 P99

输出：终端摘要 + JSON 报告文件
```

### 6.3 字段匹配规则

| 字段类型 | 匹配方式 | 阈值 |
|----------|----------|------|
| province | 模糊匹配（"广东" = "广东省"） | 精确 |
| subject_type | 标准化后比较 | 精确 |
| score | 数值比较 | ±10 分 |
| riasec 各维 | 数值差值 | <= 2 |
| list 字段 | Jaccard 相似度 | >= 0.7 |
| concern_dimensions | 关键词包含 | >= 0.7 |

### 6.4 CI 集成

在 `.github/workflows/backend-ci.yml` 末尾添加：

```yaml
- name: Run accuracy benchmarks
  run: python tests/benchmarks/run_accuracy.py --output accuracy_report.json
- name: Check accuracy thresholds
  run: |
    python -c "
    import json
    r = json.load(open('accuracy_report.json'))
    if r['kb_accuracy'] < 0.95 or r['extract_accuracy'] < 0.95:
        print(f'::warning ::Accuracy below 95%: KB={r[\"kb_accuracy\"]:.1%}, Extract={r[\"extract_accuracy\"]:.1%}')
    "
```

---

## 7. Section 5：B3 交互体验优化（Phase 2，深化 B1 基础）

B1 已完成基础版本（渐进式提问 system prompt + 信息确认回显），B3 在此之上深化：

- **心理引导对话流增强**：根据画像完整度动态调整提问策略（L1 补基础信息 / L2 深挖兴趣 / L3 探索价值观），增加情绪感知调整语气
- **信息确认回显优化**：LLM 提取到关键信息时，在回复前端展示"已了解"气泡确认（"已记录：广东·物理类·600分 ✓"）
- **进度指示**：mini-app 聊天界面顶部显示画像完整度进度条（L1→L2→L3），SSE `profile_updated` 事件推送实时百分比

---

## 8. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/services/cend_profile_analyzer.py` | 新建 | C-end LLM 档案提取器 |
| `backend/services/profile_bridge.py` | 新建 | 提取→存储桥接层 |
| `backend/api/routes/miniapp.py` | 修改 | SSE 结束后触发桥接，LLM 提取主路径 + 正则 fallback |
| `backend/analytics/topic_cloud.py` | 修改 | 新增从 session_profiles.profile_json.concerns 读取关注维度数据源 |
| `tests/benchmarks/knowledge_qa.json` | 新建 | KB ground truth 数据集 |
| `tests/benchmarks/profile_extraction.json` | 新建 | 提取 ground truth 数据集 |
| `tests/benchmarks/run_accuracy.py` | 新建 | 准确度评测脚本 |
| `tests/benchmarks/__init__.py` | 新建 | 包初始化 |
| `.github/workflows/backend-ci.yml` | 修改 | 添加 benchmark 步骤 |
| `.gitignore` | 修改 | 添加 `data/extracted_profiles/` |
| `data/extracted_profiles/` | 新建目录 | JSON 备份存储 |

---

## 9. 测试策略

遵循 `.claude/rules/testing.md` 的 HARD RULE（实现与测试由不同子代理编写）：

| 测试文件 | 类型 | 覆盖 |
|----------|------|------|
| `tests/unit/test_cend_profile_analyzer.py` | 单元 | prompt 构造、JSON 解析、增量提取 |
| `tests/unit/test_profile_bridge.py` | 单元 | merge 逻辑、completeness 计算 |
| `tests/integration/test_cend_data_pipeline.py` | 集成 | SSE → 提取 → session_profiles 端到端 |
| `tests/benchmarks/run_accuracy.py` | 基准 | KB + 提取准确度 |

**边界覆盖（强制）：**
- 正常路径：标准对话提取
- 空输入：空对话 → 空 profile
- 超长输入：100+ 轮对话 → 截断
- 格式错误：非 JSON LLM 输出 → fallback
- 并发安全：2 个 SSE 连接 → 独立 session_profiles
- 租户隔离：租户 A 不能读取租户 B 的 session_profiles
