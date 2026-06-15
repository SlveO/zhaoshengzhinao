# 招生智脑 产品化发展路线图

> 最后更新：2026-06-16 | 当前阶段：Phase 1 — 基础能力补齐

---

## 项目愿景

将"招生智脑"从功能原型推进到能够投入真实高校招生场景的 B2B SaaS 产品。核心目标：
- **AI 咨询**：学生通过 mini-app 获得准确、个性化、有引导性的招生咨询服务
- **数据闭环**：每次对话自动提取画像 → 意向评分 → 招生老师获得可行动的情报和可视化报告

---

## 团队分工

| 成员 | 模块 | Phase 1 核心交付 | Phase 2 | Phase 3 |
|------|------|-------------------|----------|----------|
| **A** | 知识库 | 数据收集与导入（多省份录取数据、SCNU 专题 FAQ 扩充） | 知识质量迭代 | 自动化采集 + 更新 |
| **B** | AI 咨询 | ① 数据链路打通（LLM 提取 → session_profiles） ② 准确度测试框架 | 交互体验优化（心理引导、进度条、信息回显） | 多模型 A/B 测试 |
| **C** | 数据闭环 | ① 意向评分模型（规则型） ② 线索总览 API | 后台跟进系统（LeadWorkbench 真实化） | 预测型评分 + 自动招生建议 |

---

## Phase 1: 基础能力补齐（当前阶段）

**时间**：Week 1-2

**目标**：修复关键数据链路断裂，建立可量化的质量评估体系，打通从对话到分析看板的端到端数据流。

### B — AI 咨询体系

#### B1. C-end 数据链路打通（B2 优先级最高）

将 mini-app 的 profile 提取从正则升级为 LLM 驱动：

```
Mini-app SSE
  → LLM 对话（含心理引导 prompt，渐进式提取学生信息）
  → profile_analyzer LLM 提取（省份/选科/分数/兴趣/关注维度/RIASEC/其他）
  → session_profiles 表（profile_json JSONB, confidence_json JSONB, completeness）
  → 3 个分析看板实时消费（profile_dashboard / region_distribution / competitive_analysis）
```

**关键文件**：
- `backend/services/consult_service.py` — 升级 `extract_profile_from_message()`
- `backend/agents/conversation/profile_analyzer.py` — 扩展 prompt 模板适配 C-end 字段
- `backend/services/profile_bridge.py` — **新建**，桥接 mini-app session → session_profiles
- `backend/tenants/models.py` — SessionProfile 表（已定义、有 SQL，只需数据写入）
- `data/extracted_profiles/` — 开发阶段 JSON 文件备份（已 gitignored）

**提取字段体系**：

| 层级 | 字段 | 类型 | session_profiles JSON 路径 |
|------|------|------|---------------------------|
| 基础信息 | province, subject_type, score | string/string/int | `profile_json.basic` |
| 个人兴趣 | preferred_subjects, strong_subjects, hobbies | list[string] | `profile_json.interests` |
| 关注维度 | concern_dimensions | list[string] 自由标签 | `profile_json.concerns` |
| RIASEC | R, I, A, S, E, C | int 1-10 | `profile_json.riasec` |
| 价值观 | values_ranking | list[string] | `profile_json.values` |
| 地域偏好 | region_pref | {province, city} | `profile_json.region_pref` |
| 其他 | extra | dict | `profile_json.extra` |

#### B2. 准确度测试框架

- `tests/benchmarks/knowledge_qa.json` — ≥100 对标准问答（覆盖录取分数/课程/就业/校园生活）
- `tests/benchmarks/profile_extraction.json` — ≥50 对对话+标注
- `tests/benchmarks/run_accuracy.py` — LLM-as-judge 评分 + 字段对比 + 速度记录
- 目标：KB 正确率 ≥ 95%，提取准确率 ≥ 95%

#### B3. 交互体验优化（Phase 2）

- LLM prompt 中注入温和心理引导话术（避免审讯式）
- 关键信息自然回显确认
- mini-app 聊天界面画像完整度进度条

### C — 数据闭环

#### C1. 意向评分模型（规则型，第一代）

```
意向分 (0-100) = 基础分(30) + 互动分(30) + 匹配分(20) + 时效分(20)

基础分：省份在招生省 +10 | 选科匹配 +10 | 分数过线 +10
互动分：对话轮次×2(max10) + 有意向专业+10 + 完整度L2+5 L3+10
匹配分：学生RIASEC与学校优势专业的余弦相似度 × 20
时效分：活跃<7天=20 | <14天=14 | <30天=8 | >30天=0
```

**优先级**：P0(80-100) 24h电话 | P1(60-79) 48h微信 | P2(40-59) 培育 | P3(0-39) 推送

#### C2. 标签体系

```yaml
事实标签: province, subject_type, score, intent_majors, session_count, last_active_at
模型标签: riasec_type, completeness, concern_dimensions
预测标签: intent_score, priority, predicted_major_match, followup_suggestion (LLM生成)
业务标签: stage(new/contacted/qualified/applied/enrolled/lost), assigned_counselor
```

#### C3. 可视化报告与招生建议

- `GET /api/v1/admin/analytics/lead-summary` — 线索总览（优先级分布、阶段漏斗、趋势）
- `GET /api/v1/admin/analytics/recruitment-insights` — LLM 生成的自然语言招生建议（定时或手动触发）
- 10 个已有分析看板中的 7 个直接可用（3 个依赖 B2 完成后恢复）
- 关注维度词云接入 `topic_cloud` 看板

---

## Phase 2: 交互与跟进（Week 2-3）

**目标**：解决"招生老师能做什么"的问题。

### B
- 交互体验优化（B3）完整实施
- 准确度测试框架（B1）完整运行 + CI 集成
- 根据测试结果迭代 prompt

### C
- **后台跟进系统（C2）**：
  - 新 API：`GET/PUT /api/v1/admin/leads`、`POST /api/v1/admin/leads/{id}/notes`
  - LeadWorkbenchPage 从 mock 切换为真实 API
  - 线索状态流转（new → contacted → qualified → applied → enrolled/lost）
  - 跟进备注系统

---

## Phase 3: 联调与上线（Week 3-4）

**目标**：端到端测试，投入真实使用。

- 三方集成联调（A 的知识库 → B 的咨询链路 → C 的数据闭环）
- 真实学生对话测试（≥50 人）
- 准确度复测（确保 95% 阈值）
- 上线发布 + 监控

---

## 长期演进路线（Phase 4+）

### 评分模型进化

| 阶段 | 模型 | 数据需求 | 时机 |
|------|------|----------|------|
| **当前** | 规则型（人工加权） | 无，规则直接定义 | Phase 1 |
| **Phase 4** | 混合型（规则 + 行为） | 积累 ≥500 条学生对话，引入相对分（pool rank） | 运行 1-2 月后 |
| **Phase 5** | 预测型（ML 模型） | ≥2000 条带 enrollment 结果的历史数据 | 运行 3-6 月后 |

### 数据闭环增强

- **渠道归因**：追踪学生来源渠道（网站/小程序/微信/线下），分析各渠道转化率
- **A/B 测试**：不同 prompt、温度、推荐策略的效果对比
- **自动化培育**：P2/P3 线索自动推送内容（招生简章、专业介绍、校园活动）直到升级
- **流失预警**：检测长期不活跃的高意向线索，自动提醒招生老师

### 多租户扩展

- 当前 SCNU 单租户 → 支持新增高校租户
- 每个租户独立的：知识库、RIASEC 基准权重、意向评分阈值、招生省份
- 管理后台多租户切换

---

## 关键技术决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| C-end 提取方式 | LLM 提取（复用 B2B profile_analyzer 模式） | 正则无法处理自然语言中的隐性信息（兴趣、价值观、RIASEC） |
| 提取存储 | session_profiles 表 + 开发阶段 .json 备份 | session_profiles 是 3 个分析看板的数据源，必须写入；JSON 备份便于开发调试 |
| 评分模型起点 | 规则型 | 无历史 enrollment 数据无法训练 ML 模型；规则型可立即上线，后续迭代 |
| 准确度评测 | LLM-as-judge + 人工标注 ground truth | 人工标注提供基准，LLM-as-judge 自动评分可规模化 |
| 关注维度标签 | 自由标签（非预设枚举） | 学生关注点是开放多样的，预设枚举会限制洞察 |

---

## 相关文档

- `CLAUDE.md` — 项目架构与开发约定
- `docs/ARCHITECTURE.md` — 技术架构详解
- `docs/DEVELOPER.md` — 协作者上手指南
- `.claude/plans/purring-splashing-gadget.md` — 当前阶段详细执行计划
