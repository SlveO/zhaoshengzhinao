# 招生智脑 V2 优化 — 工程设计方案

> 状态: 设计中 | 日期: 2026-05-19 | 范围: 4 子系统并行 | 策略: Web-first, 后续迁移小程序

---

## 总体策略

四个子系统互不冲突，可 4 session 并行推进。全部 web-first（H5 + Admin SPA），后续复用代码迁移到小程序。

---

## A: 学生主页面（跨院校对比推荐）

**分支**: `feat/compare-page` | **触碰**: mini-app H5 + backend

### 新增 API

```
GET /api/v1/compare/recommendations?profile_id={id}
  → 遍历所有 active tenants
  → 每 tenant 查 ChromaDB collection
  → 画像匹配度排序
  → 返回 Top-10 院校 × Top-3 专业
```

### 新增页面

`mini-app/src/pages/compare/index.vue` — 院校卡片列表 + 点开专业详情 + 多选对比

### 路由

`/pages/compare/index` — 从 chat 页面"推荐"按钮跳转

---

## B: 输出路由（双 Agent 智能路由）

**分支**: `feat/dual-agent` | **触碰**: backend chat handler

### 方案

不改 LangGraph 结构。在 chat handler 的消息处理段做路由：

```
用户消息 → 类型判断(关键词) →
  ├── 事实性问题 → B2B 招生 agent (temp 0.3)
  └── 个人表达 → 心理引导 agent (temp 0.7)
→ 直接输出对应 agent 回答
```

### 消息类型判断

```python
FACTUAL_KEYWORDS = ["分数线", "就业", "薪资", "课程", "宿舍", "食堂", "多少分", "学费"]
PSYCH_KEYWORDS = ["喜欢", "担心", "害怕", "迷茫", "不知道", "纠结", "压力"]
```

### 碰的文件

仅 `backend/api/routes/chat.py`

---

## C: 增强分析（关键词 + 情绪 + 热点）

**分支**: `feat/enhanced-analytics` | **触碰**: backend analytics + admin-spa

### 新增 3 个模块

| 模块 | 数据 | 展示 |
|------|------|------|
| topic-cloud | chat.message_sent 内容 → jieba 分词 → 词频 | ECharts wordCloud |
| emotion-timeline | chat.message_sent payload.emotion | 折线图 |
| hot-questions | 消息聚类 | Top-10 柱状图 |

### 碰的文件

- `backend/analytics/topic_cloud.py`
- `backend/analytics/emotion_timeline.py`
- `backend/analytics/hot_questions.py`
- `admin-spa/src/pages/InsightsPage.tsx` — 新页面

---

## D: 可定制 Agent

**分支**: `feat/custom-agent` | **触碰**: backend + admin-spa

### 定制项

| 定制项 | 存储 | 实现 |
|--------|------|------|
| 自定义提示词 | `tenant.config.ai_persona.custom_prompt` | chat route 读取覆盖默认 |
| 对话风格 | `ai_persona.style` (formal/casual) | 拼入提示词 |
| 是否主动推荐 | `ai_persona.proactive_recommend` (bool) | 控制推荐时机 |

### 碰的文件

- `backend/api/routes/chat.py` — prompt 选择
- `backend/admin/router.py` — persona CRUD
- `admin-spa/src/pages/AgentSettingsPage.tsx` — 新页面

---

## 并行隔离

```
backend/analytics/  ← C 独占
backend/api/routes/chat.py  ← B + D 共享（需协调，见下文）
admin-spa/src/pages/InsightsPage.tsx   ← C 独占
admin-spa/src/pages/AgentSettingsPage.tsx ← D 独占
mini-app/src/pages/compare/  ← A 独占
```

**唯一冲突点**：B 和 D 都改 `chat.py`。合并顺序 B → D（B 只改消息处理段，D 改 prompt 选择段，不同行）。
