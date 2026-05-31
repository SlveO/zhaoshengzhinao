# Prompt A: 修复测试环境与测试代码

## 目标

修复导致测试报告（@reports/data-pipeline-test-results.md）中 1 个单元测试失败和 E2E 测试未执行的两个问题。业务代码逻辑无问题，不需要修改。

## 背景

完整分析见 @docs/data-pipeline-improvement-plan.md。

**问题 1**：`test_different_tenants_separate_urls` 断言 `'scnu' in url` 失败，实际 URL 是 `/uploads/test/{uuid}.png`。
- 根因：@backend/tests/unit/test_admin_brand.py:39-48 的 `autouse` fixture 将 `_current_tenant` 固定为 `MockTenant(slug="test")`。
  测试内部（L264-296）用 `patch.object(mw, "resolve_tenant", side_effect=resolve_by_slug)` 试图切换租户，
  但上传端点 @backend/admin/router.py:39 通过 `Depends(get_current_tenant)` 读取的是 ContextVar——patch 中间件的
  `resolve_tenant` 不会更新 `_current_tenant`。端点始终拿到 `slug="test"`。
- 修复方式：改用 @backend/core/tenant_context.py:41-42 的 `set_current_tenant()` 直接设置 ContextVar。

**问题 2**：E2E 测试（@backend/tests/e2e/ 下 5 个文件）在容器内不存在，`pytest tests/e2e/` 返回 exit code 4。
- 根因：Docker 镜像构建于测试文件创建之前（COPY 发生在构建期），docker-compose.yml 未挂载 `./backend/tests`。
- 修复方式：添加 volume mount + 重建镜像。

## 可用工具

- **Bash**：执行 docker compose 命令、git diff
- **Edit**：修改 docker-compose.yml（单行追加）
- **Agent (backend-dev)**：修复 Python 测试文件中的 mock 逻辑
- **Agent (cmd-executor)**：执行 `docker compose build` 等长时间命令

## Task 1: 修复单元测试 Mock

### 文件：@backend/tests/unit/test_admin_brand.py:264-296

**当前代码问题**（L273-276）：
```python
with patch("os.makedirs"), \
     patch("builtins.open"), \
     patch("os.path.exists", return_value=True), \
     patch.object(mw, "resolve_tenant", side_effect=resolve_by_slug):
```
`patch.object(mw, "resolve_tenant")` 无法影响 `Depends(get_current_tenant)` 读取的 ContextVar。

**修复**：在每次请求前调用 `set_current_tenant()` 直接设置 ContextVar。删除 `resolve_by_slug` 函数和 `patch.object(mw, ...)`，改用：

```python
with patch("os.makedirs"), \
     patch("builtins.open"), \
     patch("os.path.exists", return_value=True):

    # Tenant A
    set_current_tenant(MockTenant())  # 需要在 with 块内重新设置
    # 注意：MockTenant 的 slug 默认是 "test"，需要动态修改
    ...
```

**具体改动**：
1. 保留 `from unittest.mock import ...` 导入（L3）
2. 在测试方法内，将 L268-271 的 `resolve_by_slug` 函数替换为：直接构造不同 slug 的 MockTenant 并通过 `set_current_tenant()` 注入
3. 删除 L276 的 `patch.object(mw, "resolve_tenant", side_effect=resolve_by_slug)` 行
4. 在每次 `client.post(...)` 前调用 `set_current_tenant(MockTenant())`，并确保 MockTenant 实例的 slug 属性值为 `"scnu"` 和 `"sysu"`

**验证**：
```bash
docker compose exec backend python -m pytest tests/unit/test_admin_brand.py::TestBrandEndpoints::test_different_tenants_separate_urls -v --tb=short
```
期望：PASSED

## Task 2: 添加 tests volume mount

### 文件：@docker-compose.yml:49-51

在 backend 服务的 `volumes` 列表末尾追加一行：

```yaml
      - ./backend/tests:/app/tests:ro
```

位置：`- ./data/approved:/app/data/approved:ro` 之后（第 51 行之后）。

**说明**：开发环境只读挂载，新增测试文件无需重建镜像即可被容器内 pytest 发现。

**验证**：
```bash
docker compose up -d backend
docker compose exec backend ls tests/e2e/
```
期望：列出 5 个 .py 文件

## Task 3: 重建镜像（使已有 E2E 测试可用）

```bash
docker compose build backend && docker compose up -d backend
```

**验证**：
```bash
docker compose exec backend python -m pytest tests/e2e/ --collect-only -q
```
期望：collected > 0 items（不再 exit code 4）

## 执行顺序

Task 1 → Task 2 → Task 3（无依赖，可自行决定顺序）。完成后跑全量回归确认无新增失败。

## 规则

- 只修改测试代码（Task 1）和 Docker 配置（Task 2），不修改业务代码
- 每个 Task 完成后立即验证
- 遇到权限阻断记录到 @reports/block.md
