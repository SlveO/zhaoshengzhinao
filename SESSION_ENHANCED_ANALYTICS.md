# Session C: 增强分析（关键词+情绪+热点）

> 分支: `feat/enhanced-analytics` | 基于: `develop` | 碰 backend + admin-spa

## 启动

```bash
git checkout develop && git checkout -b feat/enhanced-analytics
```

必读: `docs/superpowers/specs/2026-05-19-optimization-design.md` §C

## 任务

### 1. 关键词词云 (`backend/analytics/topic_cloud.py`)

从 `event_logs` 的 `chat.message_sent` 事件中提取消息文本，用 jieba 分词生成词频统计：

```python
async def get_topic_cloud(tenant_id: str, days: int = 30) -> list[dict]:
    """Return [{word, count}] for word cloud visualization."""
    # 查所有 chat.message_sent 的 payload.content
    # jieba 分词 → 过滤停用词 → 词频 top-50
    pass
```

路由: `GET /api/v1/admin/analytics/topic-cloud`

### 2. 情绪时间线 (`backend/analytics/emotion_timeline.py`)

从 `chat.message_sent` 的 `payload.emotion` 提取情绪标签，按时间聚合：

```python
async def get_emotion_timeline(tenant_id: str, days: int = 30) -> dict:
    """Return {timeline: [{date, emotion, count}]}"""
    pass
```

路由: `GET /api/v1/admin/analytics/emotion-timeline`

### 3. 咨询热点 (`backend/analytics/hot_questions.py`)

消息按专业提及 + 主题聚类统计 Top-10：

```python
async def get_hot_questions(tenant_id: str, days: int = 30) -> list[dict]:
    """Return [{topic, count}] for bar chart."""
    pass
```

路由: `GET /api/v1/admin/analytics/hot-questions`

### 4. 管理端新页面 (`admin-spa/src/pages/InsightsPage.tsx`)

三栏布局：词云 + 情绪折线 + 热点柱状图。侧边栏加菜单项。

## 不碰

- mini-app / backend chat / tenants

## 完成标志

- [ ] 3 个 API 端点返回非空数据
- [ ] InsightsPage 展示词云、情绪线、热点图
