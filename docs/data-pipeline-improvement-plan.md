# Data Pipeline 测试执行改进方案

## 问题诊断

工作流程：定义 data pipeline → 生成测试 → 执行修复 → 跑测试验证。测试结果报告（`reports/data-pipeline-test-results.md`）仍有两个未解决问题：

| # | 问题 | 表现 | 类型 |
|---|------|------|------|
| 1 | 单元测试失败 | `test_different_tenants_separate_urls` — `assert 'scnu' in '/uploads/test/...'` | TEST（mock 缺陷） |
| 2 | E2E 测试未执行 | `pytest tests/e2e/` → exit code 4（目录不存在） | INFRA（镜像过期） |

### 问题 1 根因：Mock 设置缺陷

**文件**：`backend/tests/unit/test_admin_brand.py`

`autouse` fixture 将 `_current_tenant` 上下文变量固定为 `MockTenant(slug="test")`。测试内部用 `patch.object(mw, "resolve_tenant")` 试图切换租户，但上传端点通过 `Depends(get_current_tenant)` 读取上下文变量——patch 中间件不影响该变量。端点始终拿到 `slug="test"`，URL 始终是 `/uploads/test/{uuid}.png`，断言 `'scnu' in url` 必然失败。

代码逻辑正确（URL 包含 tenant slug），测试的 mock 方式有 bug。

**修复**：测试应在每次请求前显式调用 `set_current_tenant(MockTenant(slug="scnu"))`，而非 patch 中间件模块。

### 问题 2 根因：Docker 镜像过期

| 时间点 | 事件 |
|--------|------|
| 2026-05-29 01:20 | Docker 镜像构建（`COPY backend/ /app/`） |
| 2026-05-29 03:21-03:22 | E2E 测试文件创建（`backend/tests/e2e/` 下 5 个文件） |

镜像构建时 `backend/tests/e2e/` 不存在，`COPY` 指令未将其打包。`docker-compose.yml` 没有挂载 `./backend/tests`。验证：`docker compose exec backend ls tests/e2e/` → `No such file or directory`。

**修复**：重建镜像 + 添加 volume mount 防止复发。

---

## 改进措施

### 立即修复（P0）

| 操作 | 文件 | 说明 |
|------|------|------|
| 修复 mock | `backend/tests/unit/test_admin_brand.py` | `set_current_tenant()` 替代 `patch.object(resolve_tenant)` |
| 添加 volume | `docker-compose.yml` | `./backend/tests:/app/tests:ro` 使新增测试无需重建镜像即可执行 |
| 重建镜像 | Docker | `docker compose build backend && docker compose up -d backend` |

### 流程改进（P1）

| 操作 | 文件 | 说明 |
|------|------|------|
| Phase 0 环境检查 | `docs/data-pipeline-test-execution-v2.md` | 测试执行前验证容器内目录存在 + `--collect-only` |
| 失败分类 | 测试结果报告模板 | 每个失败标注 `CODE \| TEST \| INFRA` 类型 |
| 容器同步策略 | `docker-compose.yml` | 开发环境 volume mount，CI 环境 `--build` |

### 防护措施（P2）

- 新增测试文件后，如未配置 volume mount，必须 `docker compose build` 重建
- 测试执行 prompt 增加前置条件检查（Phase 0），不满足时阻塞并给出修复指令
- 失败分类引入报告模板，避免测试 bug 被当作代码 bug 处理

---

## 验证清单

- [ ] `pytest tests/unit/test_admin_brand.py::TestBrandEndpoints::test_different_tenants_separate_urls -v` → PASSED
- [ ] `docker compose exec backend python -m pytest tests/e2e/ -v` → 收集到 4+ 测试并执行
- [ ] 在宿主机新建 `backend/tests/e2e/test_new.py`，不重建镜像直接 `pytest tests/e2e/` 可收集到（volume mount 生效）
- [ ] `pytest tests/ -v` 全量回归无失败
