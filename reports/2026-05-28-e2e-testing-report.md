# E2E Testing Report — feat/admin-redesign-v2

> 日期：2026-05-28 | 分支：feat/admin-redesign-v2

## 验证项 1-3：UI 端到端测试 ✅

| # | 验证项 | 方法 | 结果 |
|---|--------|------|------|
| 1 | Brand 品牌配置页 | Playwright | 通过 — 登录、字段渲染、上传/保存按钮正常 |
| 2 | Knowledge 知识库页 | Playwright | 通过 — 索引状态、上传/重索引、文档表格正常 |
| 3 | Mini-app 聊天 RAG | Playwright | 通过 — AI 回复正常，无控制台错误 |

## 验证项 4：Pytest 批量测试

结果：94 passed / 2 failed / 143 errors

### 已修复的 Bug

#### Bug 1：`_make_db_mock` 缺少 AsyncMock commit

- **文件**：`backend/tests/unit/test_admin_knowledge.py:54`
- **修复前**：
  ```python
  db = MagicMock()
  db.execute = AsyncMock(return_value=execute_return, side_effect=execute_side_effect)
  return db
  ```
- **修复后**：
  ```python
  db = MagicMock()
  db.execute = AsyncMock(return_value=execute_return, side_effect=execute_side_effect)
  db.commit = AsyncMock()
  return db
  ```
- **原因**：`admin/router.py:114,118,151` 调用 `await db.commit()`，MagicMock 不可 await
- **影响**：5 个 knowledge 测试失败
- **状态**：✅ 已修复并验证

#### Bug 2：Brand 测试 `test_different_tenants_separate_urls` mock 错误

- **文件**：`backend/tests/unit/test_admin_brand.py:264-296`
- **原因**：autouse fixture（第 42 行）的 `resolve_tenant` mock 始终返回 `MockTenant(slug="test")`，忽略 X-Tenant header 值
- **修复**：在测试的 `with` 块内使用 `patch.object(mw, "resolve_tenant", side_effect=resolve_by_slug)` 覆盖 autouse fixture 的 mock，`resolve_by_slug` 根据 header 返回正确 slug
- **状态**：✅ 已修复并验证

---

## 所有 Error 详细分析

### Error 1：conftest.py teardown — InterfaceError（143 个）

**位置：**

`backend/tests/conftest.py:31-42` — session-scoped event_loop
```python
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    import models
    importlib.reload(models)
    yield loop
    loop.close()
```

`backend/tests/conftest.py:45,75-80` — autouse setup_db teardown
```python
@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    ...
    yield
    async with async_session() as db:
        for table in ["event_logs", "session_profiles", ...]:
            await db.execute(text(f"DELETE FROM {table}"))  # line 79
        await db.commit()
```

**问题：** session-scoped event_loop（第 34 行）使所有测试共享同一个异步事件循环。autouse fixture 在每个测试 teardown（第 75-80 行）执行 `DELETE FROM` 时，前一个测试的数据库连接尚未完全释放，asyncpg 抛出：

```
InterfaceError: cannot perform operation: another operation is in progress
```

此错误发生在 fixture teardown 阶段，不在测试逻辑内。它导致级联——第一个 teardown 失败后，后续测试的 setup 因连接池污染也失败。

**严重度**：高（143 个错误）

**建议修复**：将 `event_loop` fixture scope 从 `session` 改为 `function`，或改为每个测试创建/销毁独立的 event_loop。

---

### Error 2：test_upload_no_filename — 422 != 200

**测试代码**：`backend/tests/unit/test_admin_knowledge.py:205`
```python
files={"file": ("", io.BytesIO(b"content"), "text/plain")}  # 空文件名
```

**路由签名**：`backend/admin/router.py:82-83`
```python
async def upload_document(
    file: UploadFile = File(...),
    data_type: str = Form(...),
```

**问题：** FastAPI/Starlette 在 `UploadFile` 验证层检查 filename 非空。空字符串文件名触发 Pydantic 验证，返回 422 Unprocessable Entity。请求未到达路由处理函数。

**严重度**：低 — 测试设计问题，框架正确拒绝了空文件名。测试期望应为 422 而非 200。

---

### Error 3：test_upload_when_import_excel_raises — RuntimeError 穿透

**测试代码**：`backend/tests/unit/test_admin_knowledge.py:224`
```python
mock_import.side_effect = RuntimeError("Excel parse failed")
```

**路由代码**：`backend/admin/router.py:97-122`
```python
try:
    if suffix in (".xlsx", ".xls"):
        result = await import_excel(...)  # RuntimeError 在此抛出
    ...
finally:
    os.unlink(tmp_path)
```

**问题：** 路由的 `try` 块只有 `finally`，没有 `except`。RuntimeError 穿透到 FastAPI 返回 500。同时 mock 的 `os.unlink` 与真实 `tempfile.NamedTemporaryFile` 交互产生文件系统混乱。

**严重度**：低 — 测试设计问题，需要 mock `tempfile.NamedTemporaryFile` 或让路由 `except Exception` 捕获。

---

## 基础设施问题（已知）

`backend/tests/conftest.py` 的设计冲突：
- `event_loop` fixture scope=`session` → 所有测试共享同一事件循环
- `setup_db` fixture autouse=True → 每个测试 teardown 操作数据库
- 导致批量运行时 asyncpg 连接池竞争

此问题在 `.claude/SESSION_STATE.md` 中已记录，需要架构层面解决。单独运行测试时不出现。
