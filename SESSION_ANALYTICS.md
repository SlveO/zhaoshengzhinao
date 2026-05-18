# Session 指令：Analytics 轨道

> 分支: `feat/analytics` | 基于: `develop` | 与 Data Onboarding 轨道零文件冲突

---

## 启动清单

### 1. 阅读文档

| 顺序 | 文件 | 关注内容 |
|------|------|---------|
| 1 | `COLLABORATION.md` | 分支策略、Session 启动/结束流程 |
| 2 | `CONVENTIONS.md` | Python 规范、API 契约 §2.3、event_logs 表结构 |
| 3 | `SESSION_STATE.md` | 确认 Analytics 轨道 ⬜，启动后更新为 🔵 |
| 4 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §2 | 模块依赖链——了解哪些模块依赖于哪些数据 |
| 5 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §3.1 | event_logs 表结构 + payload 规范 |

### 2. 创建分支

```bash
git checkout develop
git checkout -b feat/analytics
```

### 3. 确认 Foundation 可用

```bash
docker compose up -d db redis
cd backend
DATABASE_URL="postgresql+asyncpg://gaokao:gaokao@localhost:5432/gaokao" python -c "
from main import app; print('Backend loaded OK')
"
```

### 4. 更新状态

编辑 `SESSION_STATE.md`，将 Analytics 轨道改为 `🔵 进行中`。

---

## 工作内容

### 目标

将 `backend/analytics/` 目录下的 7 个 stub 端点替换为真实的 SQL 聚合查询。所有数据从 `event_logs` 和 `session_profiles` 表聚合。

### 你要修改的文件

```
backend/analytics/
├── router.py                  # [修改] 移除 _stub 标记，改为调用真实查询
├── funnel.py                  # [创建] 招生漏斗查询
├── profile_dashboard.py       # [创建] 画像看板聚合（已部分实现，补充完整）
├── major_heatmap.py           # [创建] 专业热度查询
├── region_distribution.py     # [创建] 生源地域分布查询
├── competitive_analysis.py    # [创建] 对比维度 + 流失分析
├── dialogue_quality.py        # [创建] 对话质量指标
└── annual_report.py           # [创建] 年度报告聚合
```

### 不碰的文件

```
admin-spa/        ← Admin SPA 轨道产出，不要改
mini-app/         ← Mini-App 轨道产出，不要改
backend/data/     ← Data Onboarding 轨道工作区，不要改
backend/admin/    ← Data Onboarding 轨道可能修改，不要碰 router.py
```

### 依赖关系

```
event_logs 表 (已有，在 Foundation 轨道完成)
    │
    ├── funnel.py — 聚合 page.viewed + chat.message_sent + page.intent_expressed
    │
    ├── major_heatmap.py — 聚合 recommendation.generated + recommendation.feedback
    │   依赖: funnel 数据（要算"咨询→意向"转化率）
    │
    ├── region_distribution.py — 聚合 profile.updated + session_profiles
    │
    ├── competitive_analysis.py — 聚合 chat.message_sent 中的院校提及 + profile.updated
    │   依赖: funnel 数据 + profile_dashboard 数据
    │
    ├── dialogue_quality.py — 聚合 chat.message_sent + recommendation.feedback
    │
    └── annual_report.py — 聚合上面所有模块的数据
        依赖: ①funnel ②profile_dashboard ④major_heatmap ⑤region_distribution ⑥competitive_analysis
        模块依赖链在 core/module_registry.py 中已定义
```

### 每个模块的开发流程

以 `funnel.py` 为例：

```python
# analytics/funnel.py
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from models import async_session

async def get_funnel(tenant_id: str, days: int = 365) -> dict:
    """从 event_logs 计算招生漏斗各层转化率"""
    async with async_session() as db:
        # Layer 1: Visitors (page.viewed 去重 user_id)
        visitors = await db.execute(text("""
            SELECT COUNT(DISTINCT user_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'page.viewed'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": datetime.now(timezone.utc) - timedelta(days=days)})
        visitor_count = visitors.scalar() or 0

        # Layer 2: Conversations (chat.message_sent 去重 session_id)
        conversations = await db.execute(text("""
            SELECT COUNT(DISTINCT session_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'chat.message_sent'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": datetime.now(timezone.utc) - timedelta(days=days)})
        conversation_count = conversations.scalar() or 0

        # Layer 3: Deep consultations (profile.updated with completeness >= L2)
        deep = await db.execute(text("""
            SELECT COUNT(DISTINCT session_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'profile.updated'
              AND payload->>'completeness' IN ('L2', 'L3')
              AND created_at >= :since
        """), {"tid": tenant_id, "since": datetime.now(timezone.utc) - timedelta(days=days)})
        deep_count = deep.scalar() or 0

        # Layer 4: Intent expressed
        intent = await db.execute(text("""
            SELECT COUNT(DISTINCT user_id)
            FROM event_logs
            WHERE tenant_id = :tid
              AND event_type = 'page.intent_expressed'
              AND created_at >= :since
        """), {"tid": tenant_id, "since": datetime.now(timezone.utc) - timedelta(days=days)})
        intent_count = intent.scalar() or 0

        # Layer 5: Enrolled (placeholder - 需要院校回传录取数据)
        enrolled_count = 0

    return {
        "period": {
            "start": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
        },
        "stages": {
            "visitors": visitor_count,
            "conversations": conversation_count,
            "deepConsultations": deep_count,
            "intentExpressed": intent_count,
            "enrolled": enrolled_count,
        },
        "conversionRates": {
            "visitorToConversation": round(conversation_count / visitor_count * 100, 1) if visitor_count else 0,
            "conversationToDeep": round(deep_count / conversation_count * 100, 1) if conversation_count else 0,
            "deepToIntent": round(intent_count / deep_count * 100, 1) if deep_count else 0,
            "intentToEnrolled": 0,  # placeholder
        },
    }
```

### 更新 router.py

将每个 stub 端点替换为调用真实查询：

```python
# analytics/router.py — 改一个端点的例子
@router.get("/funnel")
async def funnel(
    tenant=Depends(_require(ModuleKey.FUNNEL)),
    days: int = 365,
):
    from analytics.funnel import get_funnel
    return await get_funnel(str(tenant.id), days=days)
```

### TDD 方式

每个模块先写测试再写实现：

```python
# tests/unit/test_analytics_funnel.py
import pytest
from analytics.funnel import get_funnel

@pytest.mark.asyncio
async def test_funnel_returns_empty_when_no_events():
    result = await get_funnel("nonexistent-tenant-id", days=1)
    assert result["stages"]["visitors"] == 0
    assert result["stages"]["conversations"] == 0


@pytest.mark.asyncio
async def test_funnel_has_all_five_stages():
    result = await get_funnel("test-tenant-id", days=1)
    assert set(result["stages"].keys()) == {
        "visitors", "conversations", "deepConsultations", "intentExpressed", "enrolled"
    }


@pytest.mark.asyncio
async def test_funnel_conversion_rates_sum_to_valid_range():
    result = await get_funnel("test-tenant-id", days=1)
    for rate in result["conversionRates"].values():
        assert 0 <= rate <= 100
```

---

## API 输出契约（前端依赖这些字段名）

Admin SPA 已经根据这些字段名写了页面，不要改字段名：

| 端点 | 前端期望的响应结构 |
|------|------------------|
| `GET /analytics/funnel` | `{ period, stages: {visitors, conversations, deepConsultations, intentExpressed, enrolled}, conversionRates }` |
| `GET /analytics/profile-dashboard` | `{ riasecDistribution: [{dimension, avgScore, count}], valuesDistribution: [{value, percentage}], completenessBreakdown: [{level, count}], totalProfiles }` |
| `GET /analytics/major-heatmap` | `{ majors: [{majorName, consultationCount, recommendationCount, intentCount, heatScore}] }` |
| `GET /analytics/region-distribution` | `{ regions: [{province, city, studentCount, avgScore}] }` |
| `GET /analytics/competitive` | `{ comparisonDimensions: [{dimension, ourScore, competitorAvgScore}], lossAnalysis: [{reason, percentage}] }` |
| `GET /analytics/dialogue-quality` | `{ metrics: { avgTurnsPerSession, completionRate, avgSatisfaction, topQuestions: [{question, count}] } }` |
| `GET /analytics/annual-report` | `{ report: { year, summary, sections: [{title, content, charts}] } }` |

---

## 每日维护

### 开始时
```bash
git pull origin feat/analytics
```
读 `SESSION_STATE.md` 确认状态。

### 结束时
```bash
git push origin feat/analytics
```
更新 `SESSION_STATE.md` 的 Analytics 轨道行。

---

## 完成标志

- [ ] `pytest tests/unit/test_analytics_*.py -v` 全部通过
- [ ] 7 个 analytics 端点全部返回非 stub 数据
- [ ] 模块开关中间件正确控制访问（未开通模块 → 403）
- [ ] Admin SPA 的漏斗页面和画像页面展示真实数据（可选，需前端也在运行）
