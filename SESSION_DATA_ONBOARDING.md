# Session 指令：Data Onboarding 轨道

> 分支: `feat/data-onboarding` | 基于: `develop` | 与 Analytics 轨道零文件冲突

---

## 启动清单

### 1. 阅读文档

| 顺序 | 文件 | 关注内容 |
|------|------|---------|
| 1 | `COLLABORATION.md` | 分支策略、Session 启动/结束流程 |
| 2 | `CONVENTIONS.md` | Python 规范、数据库规范 §3 |
| 3 | `SESSION_STATE.md` | 确认 Data Onboarding 轨道 ⬜，启动后更新为 🔵 |
| 4 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §7 | 六级数据接入方案（L0-L5） |
| 5 | `docs/superpowers/specs/2026-05-18-b2b-platform-design.md` §3.1 | TenantData 模型 + ChromaDB collection 结构 |

### 2. 创建分支

```bash
git checkout develop
git checkout -b feat/data-onboarding
```

### 3. 确认 Foundation 可用

```bash
docker compose up -d db redis
cd backend
DATABASE_URL="postgresql+asyncpg://gaokao:gaokao@localhost:5432/gaokao" python -c "
from tenants.models import TenantData; from knowledge.indexer import index_tenant_data
print('Dependencies loaded OK')
"
```

### 4. 更新状态

编辑 `SESSION_STATE.md`，将 Data Onboarding 轨道改为 `🔵 进行中`。

---

## 工作内容

### 目标

将院校数据接入从"手动 SQL"升级为"招生办自助上传 + 自动校验 + 自动索引"。实现 L1（Excel 模板上传）和 L2（管理后台手动录入）。

### 你要创建的文件

```
backend/data/onboarding/
├── __init__.py                # [已有] 空文件
├── excel_importer.py          # [创建] Excel 解析 + 批量写入 TenantData
├── validator.py               # [创建] 数据校验函数集
└── templates/                 # [新增目录] Excel 模板文件
    ├── admission_template.xlsx    # 录取分数线模板
    ├── curriculum_template.xlsx   # 培养计划模板
    └── employment_template.xlsx   # 就业报告模板
```

### 你要修改的文件

```
backend/admin/router.py        # [修改] knowledge/documents POST — 从 stub 改为真实上传+索引
backend/admin/knowledge_config.py  # [如果存在则修改，不存在则创建] 知识库管理后端逻辑
```

### 不碰的文件

```
admin-spa/        ← Admin SPA 轨道产出
mini-app/         ← Mini-App 轨道产出
backend/analytics/  ← Analytics 轨道工作区，不要改
```

### 与 Analytics 轨道的隔离

| | Analytics | Data Onboarding |
|---|---|---|
| 工作目录 | `backend/analytics/` | `backend/data/onboarding/` |
| 可能修改的共享文件 | 无 | `backend/admin/router.py` |
| 冲突可能性 | 零 | 如果 Analytics 也改了 `admin/router.py` 才冲突（但它不改） |

---

## 实现细节

### Task D1: 数据校验器 (`validator.py`)

```python
# data/onboarding/validator.py

def validate_admission_row(row: dict) -> str | None:
    """校验单行录取数据。返回 None 表示通过，返回字符串表示错误信息。"""
    # 必填字段检查
    required = ["year", "province", "major_name", "min_score", "min_rank"]
    for field in required:
        if not row.get(field):
            return f"缺少必填字段: {field}"

    # 年份范围
    year = int(row["year"])
    if year < 2020 or year > 2030:
        return f"年份超出范围: {year}"

    # 分数范围
    score = int(row["min_score"])
    if score < 0 or score > 750:
        return f"分数超出范围: {score}"

    # 位次范围
    rank = int(row["min_rank"])
    if rank <= 0:
        return f"位次必须为正整数: {rank}"

    # 选科要求
    valid_subjects = {"物理", "历史", "不限", "物理+化学", "物理+生物", "历史+政治", "历史+地理"}
    subjects = row.get("subject_requirements", "")
    subject_list = [s.strip() for s in subjects.replace("+", " ").split()]
    # 警告但不报错

    return None


def validate_curriculum_row(row: dict) -> str | None:
    """校验培养计划数据"""
    required = ["major_name", "core_courses"]
    for field in required:
        if not row.get(field):
            return f"缺少必填字段: {field}"
    return None


def validate_employment_row(row: dict) -> str | None:
    """校验就业数据"""
    required = ["major_name", "year", "employment_rate"]
    for field in required:
        if not row.get(field):
            return f"缺少必填字段: {field}"

    rate = float(row["employment_rate"])
    if rate < 0 or rate > 100:
        return f"就业率超出 0-100 范围: {rate}"
    return None
```

### Task D2: Excel 导入器 (`excel_importer.py`)

```python
# data/onboarding/excel_importer.py
import uuid
from datetime import datetime, timezone
import openpyxl
from sqlalchemy import text

from models import async_session
from tenants.models import TenantData
from knowledge.indexer import index_tenant_data
from data.onboarding.validator import validate_admission_row, validate_curriculum_row, validate_employment_row

# data_type → (validator, expected_columns)
IMPORT_CONFIG = {
    "admission_score": (validate_admission_row, [
        "year", "province", "batch", "major_name", "min_score",
        "min_rank", "subject_requirements", "enrollment_quota"
    ]),
    "curriculum": (validate_curriculum_row, [
        "major_name", "college", "duration", "core_courses", "objective", "degree"
    ]),
    "employment": (validate_employment_row, [
        "major_name", "year", "employment_rate", "avg_salary",
        "main_industries", "typical_companies", "further_study_rate"
    ]),
}


async def import_excel(
    tenant_id: str,
    tenant_slug: str,
    file_path: str,
    data_type: str,
) -> dict:
    """导入 Excel 文件，校验、入库、触发索引，返回结果摘要"""
    validator, expected_columns = IMPORT_CONFIG[data_type]

    wb = openpyxl.load_workbook(file_path)
    ws = wb.active

    # 列名校验
    headers = [cell.value for cell in ws[1]]
    missing = [c for c in expected_columns if c not in headers]
    if missing:
        return {"success": False, "error": f"缺少列: {missing}", "imported": 0}

    rows = []
    errors = []
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        data = dict(zip(headers, row))
        err = validator(data)
        if err:
            errors.append(f"Row {i}: {err}")
        else:
            rows.append(data)

    # 去重检查（同一年同一省同一专业只保留一条）
    seen = set()
    deduped = []
    for r in rows:
        key = (r.get("year"), r.get("province"), r.get("major_name"))
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    # 批量写入 TenantData
    async with async_session() as db:
        for r in deduped:
            td = TenantData(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                data_type=data_type,
                title=f"{r.get('major_name', '')} {r.get('year', '')} {r.get('province', '')}",
                content=r,
                year=int(r.get("year", 0)) if r.get("year") else None,
                province=r.get("province", ""),
                extra_meta={
                    "major_name": r.get("major_name", ""),
                    "subject_requirements": r.get("subject_requirements", ""),
                },
            )
            db.add(td)
            # 逐条索引
            try:
                await index_tenant_data(tenant_slug, td)
                td.indexed_at = datetime.now(timezone.utc)
            except Exception as e:
                errors.append(f"Index failed for {td.title}: {e}")

        await db.commit()

    return {
        "success": True,
        "imported": len(deduped),
        "duplicates_skipped": len(rows) - len(deduped),
        "errors": errors,
        "total_rows": len(rows),
    }
```

### Task D3: 管理端知识库 API（修改 `admin/router.py`）

将 stub 的 `POST /admin/knowledge/documents` 替换为真实上传处理：

```python
# admin/router.py — 替换 knowledge/documents 的 POST 端点
import os
import tempfile

@router.post("/knowledge/documents")
async def upload_document(
    file: UploadFile = File(...),
    data_type: str = Form(...),  # admission_score / curriculum / employment / campus_life
    tenant=Depends(get_current_tenant),
    _user=Depends(get_current_tenant_user),
):
    # 保存上传文件到临时目录
    suffix = os.path.splitext(file.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        if suffix in (".xlsx", ".xls"):
            result = await import_excel(
                str(tenant.id), tenant.slug, tmp_path, data_type
            )
        else:
            # 纯文本/富文本：直接存为一条 TenantData
            content = open(tmp_path, encoding="utf-8").read()
            async with async_session() as db:
                td = TenantData(
                    id=uuid.uuid4(),
                    tenant_id=tenant.id,
                    data_type=data_type,
                    title=file.filename or "未命名文档",
                    content={"text": content},
                )
                db.add(td)
                await db.commit()
                try:
                    await index_tenant_data(tenant.slug, td)
                    td.indexed_at = datetime.now(timezone.utc)
                except Exception:
                    pass
            result = {"success": True, "imported": 1, "errors": [], "total_rows": 1}
    finally:
        os.unlink(tmp_path)

    return result
```

### Task D4: Excel 模板生成（可选，加分项）

用 openpyxl 生成带表头行的空白模板：

```python
# data/onboarding/templates/generate_templates.py
import openpyxl

def generate_admission_template(output_path: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "录取分数线"
    ws.append(["year", "province", "batch", "major_name", "min_score",
               "min_rank", "subject_requirements", "enrollment_quota"])
    # 示例行
    ws.append([2025, "广东", "本科批", "计算机科学与技术", 589, 28500, "物理", 120])
    wb.save(output_path)
```

---

## TDD 开发方式

每个模块先写测试：

```python
# tests/unit/test_excel_validator.py
from data.onboarding.validator import validate_admission_row

def test_valid_row_passes():
    row = {"year": 2025, "province": "广东", "major_name": "计科",
           "min_score": 589, "min_rank": 28500}
    assert validate_admission_row(row) is None

def test_missing_required_field():
    row = {"year": 2025, "province": "广东"}  # 缺 major_name
    err = validate_admission_row(row)
    assert err is not None
    assert "major_name" in err

def test_score_out_of_range():
    row = {"year": 2025, "province": "广东", "major_name": "计科",
           "min_score": 999, "min_rank": 28500}
    err = validate_admission_row(row)
    assert err is not None
    assert "分数" in err

def test_rank_must_be_positive():
    row = {"year": 2025, "province": "广东", "major_name": "计科",
           "min_score": 589, "min_rank": 0}
    err = validate_admission_row(row)
    assert err is not None
    assert "位次" in err
```

---

## API 输出契约

知识库管理 API（Admin SPA 的 KnowledgeSettingsPage 依赖这些）：

| 端点 | 方法 | Admin SPA 期望 |
|------|------|---------------|
| `/admin/knowledge/documents` | GET | `{ documents: [{id, title, data_type, year, indexed_at}] }` |
| `/admin/knowledge/documents` | POST | FormData: `file` + `data_type`。返回 `{ success, imported, errors }` |
| `/admin/knowledge/documents/{id}` | DELETE | 删除文档 + 从 ChromaDB 移除 |
| `/admin/knowledge/reindex` | POST | 触发租户全量重索引。返回 `{ status: "started" }` |
| `/admin/knowledge/index-status` | GET | `{ total_docs, indexed_docs, pending_docs }` |

---

## 每日维护

### 开始时
```bash
git pull origin feat/data-onboarding
```
读 `SESSION_STATE.md` 确认状态。

### 结束时
```bash
git push origin feat/data-onboarding
```
更新 `SESSION_STATE.md` 的 Data Onboarding 轨道行。

---

## 完成标志

- [ ] `pytest tests/unit/test_excel_*.py -v` 全部通过
- [ ] Excel 上传 → 校验 → 入库 → ChromaDB 索引 全链路可用
- [ ] Admin SPA 知识库管理页可上传文件并看到索引状态
- [ ] 重复上传同一文件不产生重复数据（去重生效）
- [ ] 模板文件可供招生办下载
