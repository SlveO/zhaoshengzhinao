# Session 指令：华南师范大学数据导入与系统配置

> 分支: `feat/data-scnu-import` | 基于: `develop` | 依赖 Scraper 轨道产出

---

## 启动清单

### 1. 必读文档

| 顺序 | 文件 | 关注内容 |
|------|------|---------|
| 1 | `COLLABORATION.md` | 分支策略 |
| 2 | `CONVENTIONS.md` | TenantData 模型、ChromaDB collection 结构 |
| 3 | `docs/PROJECT_MILESTONE.md` | 系统当前状态 |
| 4 | `backend/tenants/models.py` | TenantData 字段定义 |
| 5 | `backend/knowledge/indexer.py` | `index_tenant_data()` 和 `reindex_tenant()` 用法 |
| 6 | `backend/data/onboarding/excel_importer.py` | 已有导入器参考 |
| 7 | `backend/data/fixtures/default_tenant.py` | Tenant 创建示例 |

### 2. 创建分支

```bash
git checkout develop
git checkout -b feat/data-scnu-import
```

### 3. 前置条件

Scraper 轨道产出物在 `data/raw/scnu/`：

```
data/raw/scnu/
├── admissions.json        ← Scraper 轨道产出
├── curriculums.json       ← Scraper 轨道产出
├── employment.json        ← Scraper 轨道产出
├── courses.json           ← Scraper 轨道产出（可选）
└── errors.json            ← 失败项清单
```

如果 Scraper 轨道尚未完成，先用手工收集的样本数据（哪怕只有 10 个专业）验证导入流程能跑通。

---

## 工作内容

### Task 1: 创建华南师大 Tenant

在数据库中创建 SCNU tenant。**不要在 backend/data/fixtures/ 里加**——直接写一个独立脚本或通过 API 创建。

```python
# scripts/create_scnu_tenant.py
import asyncio, json, uuid
from sqlalchemy import text
from models import async_session

SCNU_TENANT = {
    "id": "20000000-0000-0000-0000-000000000002",
    "name": "华南师范大学",
    "slug": "scnu",
    "subscription_tier": "advanced",
    "status": "active",
    "config": {
        "brand": {
            "name": "华南师范大学",
            "short_name": "华南师大",
            "primary_color": "#1a3a6b",      # 华师深蓝色
            "secondary_color": "#c41230",     # 华师红
            "logo_url": "",
            "welcome_text": "欢迎了解华南师范大学！艰苦奋斗、严谨治学、求实创新、为人师表。我是你的专属AI招生顾问~"
        },
        "modules": {
            "funnel": True,
            "profile_dashboard": True,
            "major_heatmap": True,
            "region_distribution": True,
            "competitive_analysis": True,
            "dialogue_quality": True,
            "annual_report": False,
            "multi_department": False,
            "role_management": False
        },
        "knowledge_base": {"doc_count": 0, "last_updated": None},
        "mini_program": {"app_id": "", "app_secret_encrypted": ""}
    }
}

async def create():
    async with async_session() as db:
        await db.execute(text("""
            INSERT INTO tenants (id, name, slug, config, subscription_tier, status)
            VALUES (:id, :name, :slug, :config, :subscription_tier, :status)
            ON CONFLICT (slug) DO UPDATE SET config = :config
        """), {**SCNU_TENANT, "config": json.dumps(SCNU_TENANT["config"], ensure_ascii=False)})
        await db.commit()
    print("SCNU tenant created/updated")

asyncio.run(create())
```

### Task 2: 编写数据导入脚本

**文件**: `scripts/import_scnu_data.py`

这个脚本读取 `data/raw/scnu/*.json`，将数据写入 TenantData 表并触发 ChromaDB 索引。

```python
# scripts/import_scnu_data.py
import asyncio, json, uuid, os
from datetime import datetime, timezone
from models import async_session
from tenants.models import TenantData, Tenant
from knowledge.indexer import index_tenant_data, reindex_tenant
from sqlalchemy import select

DATA_DIR = "data/raw/scnu"
TENANT_SLUG = "scnu"

DATA_TYPE_MAP = {
    "admissions.json": "admission_score",
    "curriculums.json": "curriculum",
    "employment.json": "employment",
    "courses.json": "campus_life",  # 课程安排归入校园信息
}

async def import_file(tenant_id, filepath, data_type):
    with open(filepath, encoding="utf-8") as f:
        records = json.load(f)

    imported = 0
    errors = []
    async with async_session() as db:
        for r in records:
            try:
                td = TenantData(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    data_type=data_type,
                    title=r.get("title", f"{r.get('major_name', '')} {r.get('year', '')}"),
                    content=r,
                    year=r.get("year"),
                    province=r.get("province"),
                    extra_meta={
                        "major_name": r.get("major_name", ""),
                        "college": r.get("college", ""),
                    },
                )
                db.add(td)
                await db.commit()
                await index_tenant_data(TENANT_SLUG, td)
                td.indexed_at = datetime.now(timezone.utc)
                await db.commit()
                imported += 1
            except Exception as e:
                errors.append({"record": r.get("title", str(r)[:100]), "error": str(e)})

    return imported, errors

async def main():
    # 获取 SCNU tenant
    async with async_session() as db:
        result = await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        tenant = result.scalar_one_or_none()
        if not tenant:
            print("SCNU tenant not found — run create_scnu_tenant.py first")
            return
        tenant_id = tenant.id

    total = 0
    for filename, data_type in DATA_TYPE_MAP.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"SKIP {filename} — not found (Scraper track not done yet)")
            continue
        count, errs = await import_file(tenant_id, filepath, data_type)
        total += count
        print(f"{filename}: {count} imported, {len(errs)} errors")

    print(f"\nTotal: {total} documents imported to SCNU knowledge base")

    # 更新 doc_count
    async with async_session() as db:
        await db.execute(text("""
            UPDATE tenants SET config = jsonb_set(config, '{knowledge_base,doc_count}', :cnt::text::jsonb)
            WHERE slug = :slug
        """), {"cnt": total, "slug": TENANT_SLUG})
        await db.commit()

asyncio.run(main())
```

### Task 3: 数据验证

导入完成后，运行验证脚本确认数据正确入库：

```python
# scripts/verify_scnu_data.py
import asyncio
from sqlalchemy import text, select, func
from models import async_session
from tenants.models import TenantData, Tenant

async def verify():
    async with async_session() as db:
        # 获取 tenant
        result = await db.execute(select(Tenant).where(Tenant.slug == "scnu"))
        tenant = result.scalar_one_or_none()
        if not tenant:
            print("SCNU tenant not found")
            return

        # 按 data_type 统计
        result = await db.execute(text("""
            SELECT data_type, COUNT(*), COUNT(*) FILTER (WHERE indexed_at IS NOT NULL)
            FROM tenant_data
            WHERE tenant_id = :tid
            GROUP BY data_type
            ORDER BY data_type
        """), {"tid": tenant.id})

        print(f"SCNU Tenant ({tenant.name}) — Knowledge Base Status:")
        print(f"{'Data Type':<20s} {'Total':>6s} {'Indexed':>8s}")
        print("-" * 36)
        for row in result:
            print(f"{row[0]:<20s} {row[1]:>6d} {row[2]:>8d}")

        # 检查 ChromaDB 索引状态
        from knowledge.client import get_chroma_client
        client = get_chroma_client()
        try:
            coll = client.get_collection("scnu_colleges")
            count = coll.count()
            print(f"\nChromaDB 'scnu_colleges' collection: {count} documents")
        except Exception:
            print("\nChromaDB 'scnu_colleges' collection: NOT FOUND")

asyncio.run(verify())
```

### Task 4: 教务系统数据对接（可选——如果有华师学生账号）

**如果需要学生认证才能获取的数据**（如：课程详细信息、教师信息、实验室资源等），可以用学生账号登录教务系统后导出。

但就当前阶段而言，公开数据已足够。**此任务暂不执行。**

---

## 不碰的文件

```
admin-spa/        ← 不碰
mini-app/         ← 不碰
scrapers/         ← Scraper 轨道工作区，只读其产出
```

---

## 与 Scraper 轨道的接口约定

Scraper 轨道产出 → Data Import 轨道消费：

```
data/raw/scnu/admissions.json → import_scnu_data.py → TenantData (admission_score) → ChromaDB
data/raw/scnu/curriculums.json → import_scnu_data.py → TenantData (curriculum) → ChromaDB
data/raw/scnu/employment.json → import_scnu_data.py → TenantData (employment) → ChromaDB
```

**JSON 格式约定**（Scraper 轨道必须遵守，否则导入脚本解析失败）:

```json
[
  {
    "title": "计算机科学与技术 2025 广东",
    "year": 2025,
    "province": "广东",
    "major_name": "计算机科学与技术",
    "college": "计算机学院",
    "min_score": 589,
    "min_rank": 28500,
    "subject_requirements": "物理",
    "enrollment_quota": 120
  }
]
```

字段名与 `CONVENTIONS.md` 中 TenantData 的 content 字段一致。

---

## 每日维护

### 开始时
```bash
git pull origin feat/data-scnu-import
# 检查 data/raw/scnu/ 是否有 Scraper 轨道的新产出
ls -la data/raw/scnu/
```

### 结束时
```bash
git push origin feat/data-scnu-import
```

更新 `SESSION_STATE.md`。

---

## 完成标志

- [ ] SCNU tenant 创建成功（`GET /api/v1/admin/tenants/me` 返回华师品牌配置）
- [ ] 录取数据导入成功（500+ 条，ChromaDB 可检索）
- [ ] 培养计划导入成功（60+ 专业）
- [ ] 就业数据导入成功（30+ 专业/学院）
- [ ] `verify_scnu_data.py` 通过
- [ ] 管理端知识库页面可见导入的文档列表
- [ ] `GET /api/v1/admin/knowledge/index-status` 返回 indexed_docs > 0
