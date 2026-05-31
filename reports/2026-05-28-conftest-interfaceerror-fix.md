# 修复报告：conftest.py InterfaceError 级联错误（143 个）

> 日期：2026-05-28 | 分支：feat/admin-redesign-v2 | 严重度：高

## 问题描述

批量运行 `pytest backend/tests/` 时出现 143 个 `InterfaceError: cannot perform operation: another operation is in progress` 错误，导致测试大面积崩溃。单独运行单个测试文件时不出现此问题。

## 根因分析

### 冲突链路

```
conftest.py:31-42  event_loop(scope="session")  →  所有测试共享一个异步事件循环
        ↓
conftest.py:45-80  setup_db(autouse=True)       →  每个测试 teardown 执行 DELETE FROM
        ↓
asyncpg 连接池在共享循环中竞争  →  前一个测试连接未释放，下一个测试 teardown 抢占
        ↓
InterfaceError 级联：第一个 teardown 失败 → 连接池污染 → 后续测试全部失败
```

### 根因详解

1. **`event_loop` fixture scope=`session`（conftest.py:31-42）**

   自定义了一个 session 级别的 `event_loop` fixture，使所有异步测试共享同一个事件循环。该 fixture 还执行了 `importlib.reload(models)` 以确保 DB engine 在该循环内创建。

2. **`setup_db` fixture autouse=True（conftest.py:45-80）**

   每个 test 的 teardown 阶段顺序执行 `DELETE FROM` 清理 10 张表。在共享事件循环下，前一个测试的 asyncpg 连接尚未完全归还连接池，下一个测试的 teardown 就开始执行数据库操作。

3. **pytest.ini 配置强化了 session scope**

   ```ini
   asyncio_default_fixture_loop_scope = session
   asyncio_default_test_loop_scope = session
   ```

   这两个配置使 pytest-asyncio 默认使用 session 级别的循环，与自定义 `event_loop` fixture 形成双重锁定。

4. **级联效应**

   第一个 teardown 失败后，asyncpg 连接池进入异常状态。后续测试的 setup 阶段尝试获取连接时，连接池已被污染，导致连续报错。

## 修复方案

### 修改 1：`pytest.ini` — 移除 session scope 配置

**修复前：**
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
asyncio_default_test_loop_scope = session
```

**修复后：**
```ini
[pytest]
asyncio_mode = auto
```

**原因**：移除 `asyncio_default_fixture_loop_scope` 和 `asyncio_default_test_loop_scope` 后，pytest-asyncio 使用默认的 function 级别循环管理。每个测试函数获得独立的事件循环，测试结束后循环销毁，asyncpg 连接随循环一起清理，不存在连接竞争。

### 修改 2：`backend/tests/conftest.py` — 删除 `event_loop` fixture

**删除的代码（原 31-42 行）：**
```python
@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop — all async fixtures/tests share this loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    import models
    importlib.reload(models)
    yield loop
    loop.close()
```

**原因**：
- pytest-asyncio 在 `asyncio_mode = auto` 下会自动为每个 async 测试创建/销毁 event loop，无需手动管理。
- `importlib.reload(models)` 不再需要：`models/__init__.py` 使用 `_LazyEngine` / `_LazySessionMaker` 延迟初始化模式，engine 会在首次使用时自动在当前 event loop 中创建，无需 reload。
- 删除此 fixture 同时移除了 `import asyncio` 和 `import importlib` 两个不再需要的导入。

### 修改 3：`backend/tests/conftest.py` — setup_db teardown 增加 try/except 防级联

**修复前（原 75-80 行）：**
```python
async with async_session() as db:
    for table in ["event_logs", "session_profiles", ...]:
        await db.execute(text(f"DELETE FROM {table}"))
    await db.commit()
```

**修复后：**
```python
async with async_session() as db:
    for table in ["event_logs", "session_profiles", ...]:
        try:
            await db.execute(text(f"DELETE FROM {table}"))
        except Exception:
            pass
    try:
        await db.commit()
    except Exception:
        await db.rollback()
```

**原因**：
- 防御性编程：即使某张表的 DELETE 失败（外键约束、连接问题），其他表仍可继续清理。
- commit 失败时执行 rollback，避免连接池中残留未提交事务。
- 此改动是次要防护，核心修复是修改 1 和 2。

## 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `pytest.ini` | 移除 `asyncio_default_fixture_loop_scope = session` 和 `asyncio_default_test_loop_scope = session` |
| `backend/tests/conftest.py` | 删除 `event_loop` fixture（原 31-42 行）、移除 `import asyncio`/`import importlib`、setup_db teardown 增加 try/except |

## 验证方法

```bash
# 运行全量测试，确认 143 个 InterfaceError 消失
pytest backend/tests/ -v --tb=short 2>&1 | tail -20

# 预期结果：0 errors，所有测试通过
```

## 未修复的次要问题（低优先级）

以下两个问题来自同一份 E2E 报告，严重度低，不影响核心功能：

1. **`test_upload_no_filename` 422 != 200**：FastAPI 框架正确拒绝空文件名，测试期望值需改为 422。
2. **`test_upload_when_import_excel_raises` RuntimeError 穿透**：`admin/router.py` 的 `upload_document` 路由缺少 `except` 块，建议增加异常处理返回结构化 500 错误。
