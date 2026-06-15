# 招生智脑 产品化执行计划

> 最后更新：2026-06-16 | 对应路线图 Phase 1

---

## 团队分工

| 成员 | 模块 | 核心交付 |
|------|------|----------|
| **A** | 知识库搭建 | 完成知识数据收集与导入（任务细节已由 A 了解，本文不赘述） |
| **B** | AI 咨询体系 | 1. 准确度测试框架 + ground truth 数据集  2. C-end 数据链路打通（LLM 提取到 session_profiles） 3. 交互体验优化 |
| **C** | 数据闭环 | 1. 学生意向评分与标签化 2. 后台跟进高意向学生 3. 可视化数据报告与招生建议 |

---

## Module B: AI 咨询体系

### B1. C-end 数据链路打通（优先级最高）

**目标架构**：
```
Mini-app SSE -> LLM 对话（含心理引导 prompt）
  -> profile_analyzer 提取（复用 B2B 的 LLM 分析模式，适配 C-end 字段体系）
  -> 写入 session_profiles 表
  -> 分析看板实时消费
```

**提取字段体系**：

| 层级 | 字段 | 类型 | session_profiles JSON 路径 |
|------|------|------|---------------------------|
| 基础信息 | province, subject_type, score | string/string/int | profile_json.basic |
| 个人兴趣 | preferred_subjects, strong_subjects, hobbies | list[string] | profile_json.interests |
| 关注维度 | concern_dimensions | list[string] 自由标签 | profile_json.concerns |
| RIASEC | R, I, A, S, E, C | int 1-10 | profile_json.riasec |
| 价值观 | values_ranking | list[string] | profile_json.values |
| 地域偏好 | region_pref | {province, city} | profile_json.region_pref |
| 其他 | extra | dict | profile_json.extra |

**实施步骤**：

1. **升级 C-end 提取逻辑** (backend/services/consult_service.py)
   - 将 extract_profile_from_message() 从正则升级为 LLM 调用
   - 复用 profile_analyzer.py 的 prompt 模板，扩展字段定义
   - 添加心理引导 prompt 段落：在 system prompt 中注入渐进式提问策略

2. **桥接提取到 session_profiles**（新建 backend/services/profile_bridge.py）
   - 在每次对话结束后（或每 3 轮对话后）调用
   - 从 consult_sessions 读取基础信息 + 从对话历史 LLM 提取深度信息
   - 写入 session_profiles 表（merge 模式：首次创建，后续更新）
   - 计算 completeness（L1/L2/L3，复用 EvidenceAccumulator 逻辑）
   - 调用位置：backend/api/routes/miniapp.py 的 SSE 响应完成后

3. **确认分析看板数据通路**
   - profile_dashboard：RIASEC 雷达 + 价值观分布 + 完整度分布（已有 SQL 查询）
   - region_distribution：地域偏好统计（已有 SQL 查询）
   - competitive_analysis：竞争力对比（已有 SQL 查询）
   - topic_cloud：关注维度数据接入词云（从 session_profiles.profile_json.concerns 字段读取）

4. **数据存储策略（开发阶段）**
   - 同步写入 .json 文件（data/extracted_profiles/ 目录，按 session_id 命名）
   - 该目录加入 .gitignore
   - 后续集成开发时切换为仅写入 DB

### B2. 准确度测试框架

**目标**：KB 正确率 >= 95%，提取准确率 >= 95%

**交付物**：

1. **知识库问答 ground truth 数据集** (tests/benchmarks/knowledge_qa.json)
   - 目标规模：>= 100 对
   - 覆盖类别：admission_score / curriculum / employment / campus_life
   - 每对包含：question, expected_answer, source_doc, category

2. **提取准确度 ground truth 数据集** (tests/benchmarks/profile_extraction.json)
   - 目标规模：>= 50 对
   - 每对包含：完整对话 + 人工标注的 expected_extraction（所有字段）

3. **准确度评测脚本** (backend/tests/benchmarks/run_accuracy.py)
   - 知识库正确性：LLM-as-judge 评分（1-5），4+ 计为正确
   - 提取准确度：逐字段对比，按类型加权（基础信息 40% + RIASEC 30% + 兴趣/关注 30%）
   - 回复速度：SSE 首个 token 到达时间 / 完整回复时间 / P50 P95 P99
   - 输出：JSON 报告 + 终端摘要

4. **CI 集成**：在 backend-ci.yml 中加入 benchmark 步骤，阈值 < 95% 时 warning

### B3. 交互体验优化（Phase 2）

- 心理引导对话流：LLM system prompt 中加入渐进式提问策略（避免审讯式）
- 信息确认回显：LLM 提取到关键信息时自然回显确认
- 进度指示：mini-app 聊天界面显示画像完整度进度条（L1->L2->L3）

---

## Module C: 数据闭环

### C1. 学生意向评分与标签化

**评分模型（当前阶段：规则型 + 适配评分）**：

意向分 (0-100) = 基础分(0-30) + 互动分(0-30) + RIASEC匹配分(0-20) + 时效分(0-20)

**基础分 (0-30)**：
- 省份在招生省份 +10
- 选科匹配专业 +10
- 分数过线 +10

**互动分 (0-30)**：
- 对话轮次 x 2 (max 10)
- 表达了意向专业 +10
- 完整度 L2 +5, L3 +10

**RIASEC匹配分 (0-20)**：
- 学生 RIASEC 各维度与 SCNU 优势专业 RIASEC 的余弦相似度 x 20

**时效分 (0-20)**：
- 最近活跃 < 7天: 20
- 最近活跃 < 14天: 14
- 最近活跃 < 30天: 8
- 最近活跃 > 30天: 0

**优先级映射**：

| 分数 | 优先级 | 颜色 | 动作 |
|------|--------|------|------|
| 80-100 | P0 | 红色 | 24h 内电话跟进 |
| 60-79  | P1 | 橙色 | 48h 内微信联系 |
| 40-59  | P2 | 黄色 | 纳入培育流程 |
| 0-39   | P3 | 灰色 | 定期推送内容 |

**标签体系**：

事实标签：province, subject_type, score, intent_majors, session_count, last_active_at

模型标签：riasec_type（主导类型）, completeness（L1/L2/L3）, concern_dimensions（自由标签）

预测标签：intent_score（0-100）, priority（P0/P1/P2/P3）, predicted_major_match, followup_suggestion（LLM 生成）

业务标签：stage（new/contacted/qualified/applied/enrolled/lost）, assigned_counselor, last_contact_channel

**实施文件**：
- backend/services/lead_scoring.py — 新建，意向分计算 + 标签生成

### C2. 后台跟进高意向学生

**后端新 API**（路由挂载在 /api/v1/admin）：

1. GET /api/v1/admin/leads — 线索列表（分页、排序、筛选）
   - ?sort=intent_score(desc) 默认
   - ?priority=P0,P1, ?stage=new,contacted, ?date_from=2026-06-01, ?keyword=计算机

2. GET /api/v1/admin/leads/{session_id} — 线索详情
   - 完整画像 + 对话摘要 + 意向分 + 标签 + 跟进建议 + 历史备注

3. PUT /api/v1/admin/leads/{session_id}/stage — 更新线索阶段
   - body: {stage: "contacted", note: "已电话联系，初步有兴趣"}

4. POST /api/v1/admin/leads/{session_id}/notes — 添加跟进备注
   - body: {content: "...", channel: "phone"}

**LeadWorkbenchPage 改造**：替换 mock 数据为真实 API，保留现有 UI 设计

### C3. 可视化数据报告与招生建议

**后端新 API**：

1. GET /api/v1/admin/analytics/lead-summary — 线索总览（优先级分布、阶段漏斗、关注维度排名、趋势）

2. GET /api/v1/admin/analytics/recruitment-insights — LLM 生成的自然语言招生建议（可手动刷新或定时生成）

**实施文件**：
- backend/analytics/lead_summary.py — 新建，线索总览 SQL 聚合
- backend/analytics/recruitment_insights.py — 新建，LLM 招生建议生成
- 修改已有 topic_cloud.py 添加关注维度数据源

---

## 实施顺序与依赖

Phase 1 (Week 1-2):
  A: 知识库搭建（独立进行，无依赖）
  B: B2（C-end 数据链路），产出 session_profiles 数据
  C: C1（意向评分），依赖 B2 的 RIASEC 字段 -> C3（部分需 B2 数据）

Phase 2 (Week 2-3):
  B: B3（交互优化）+ B1（准确度框架，依赖 B2 稳定）
  C: C2（后台跟进，依赖 C1 评分稳定 + B2 画像数据）

Phase 3 (Week 3-4):
  三方联调 -> 真实测试（>=50 学生）-> 准确度复测 -> 上线

**关键依赖**：
- B2（C-end 数据链路）是全局阻塞点：C3 的 3 个分析看板需要 session_profiles 有数据，C1 的 RIASEC 匹配分依赖 B2 的 RIASEC 字段
- B1（准确度测试）需要 B2 的提取逻辑基本稳定后才开始
- C2（后台跟进）依赖 C1（评分模型）先有输出

---

## 验证标准

| 检查项 | 方法 | 标准 |
|--------|------|------|
| C-end 数据链路 | 启动 mini-app -> 模拟完整对话 -> 查询 session_profiles 表有记录 -> 查看 profile_dashboard 有数据 | 端到端链路完好 |
| 准确度（KB） | python backend/tests/benchmarks/run_accuracy.py | >= 95% |
| 准确度（提取） | 同上 | >= 95% |
| 意向评分 | 创建 5 个不同画像的测试对话 -> GET /api/v1/admin/leads | 意向分和优先级与预期一致 |
| 回归测试 | pytest backend/tests/ -x --tb=short | 全部通过 |
| 前端看板 | 浏览器访问 admin-spa -> LeadWorkbench 显示真实数据 | 无 mock 残留 |

---

## 测试规范（所有模块适用，强制）

> 详细测试规范见 `.claude/rules/testing.md`。以下为执行计划中的关键要求摘要。

### 独立子代理编写测试（HARD RULE）

实现代码和测试代码必须由不同的子代理实例编写，防止测试迎合实现。

```
工作流：
  1. 业务子代理（如 backend-dev）编写实现代码
  2. 独立的测试编写子代理（新 Agent 调用，同类型或不同类型）阅读代码后编写测试
  3. 测试编写子代理不得修改实现代码
  4. 测试编写子代理使用 test-runner 验证测试通过
```

### AAA 模式（强制）

每个测试函数必须遵循 Arrange-Act-Assert 结构，并用 `# Arrange` / `# Act` / `# Assert` 注释分隔。

### 测试隔离（强制）

测试互不依赖，执行顺序不影响结果。DB/Redis 状态由 `setup_db` fixture 在每个测试后清理。

### 边界条件覆盖（强制）

每个模块必须覆盖：正常路径、空/缺失输入、超长输入、格式错误、并发安全、租户隔离。

### LLM 测试特殊要求

- **Mock LLM 测试**（单元/集成）：验证 prompt 构造、JSON 解析、重试逻辑、错误处理
- **真实 LLM 测试**（benchmarks）：使用 ground truth 数据集，LLM-as-judge 评分
- **快照测试**（regression）：关键 prompt 输出保存 baseline，修改后对比差异

### 覆盖率阈值

| 类别 | 目录 | 目标 |
|------|------|------|
| 单元测试 | `tests/unit/` | 纯逻辑 90%+ |
| 集成测试 | `tests/integration/` | API 端点 80%+ |
| E2E 测试 | `tests/e2e/` | 核心用户旅程 100% |
| 准确度测试 | `tests/benchmarks/` | 评测框架 100% |

### CI 质量门禁

- lint: 0 errors → **block merge**
- unit + integration tests: 100% pass → **block merge**
- accuracy: < 95% → warning（需 PR 中解释）
- coverage: 低于阈值 → warning

### 新增模块测试门槛

- 任何新增 `backend/services/*.py` 必须有 `tests/unit/test_*.py`
- 任何新增 API 端点必须有 `tests/integration/test_*.py`
- PR 中无测试的新模块不得合并

### 测试审查清单

提交测试代码前确认：AAA 模式、测试独立、正反向覆盖、边界条件、LLM mock、精确断言、规范命名、无 sleep()、fixture 派生数据

