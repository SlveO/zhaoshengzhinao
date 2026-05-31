# Data Pipeline Test Execution (v2)

四阶段测试执行 + 环境检查 + 失败分类。执行后写入 `reports/data-pipeline-test-results.md`。

## Phase 0: Environment Check（前置）

执行任何测试前，确认环境就绪。任一步骤失败则终止，输出具体修复指令。

```
Step 0.1 — 验证测试目录在容器中存在
  docker compose exec backend ls tests/unit/ tests/integration/ tests/e2e/
  期望：三个目录均列出文件列表
  失败时：输出 "目录缺失。运行：docker compose build backend && docker compose up -d backend"
         或 "在 docker-compose.yml backend volumes 中添加：- ./backend/tests:/app/tests:ro"
         然后重试。

Step 0.2 — 验证测试可被收集
  docker compose exec backend python -m pytest tests/ --collect-only -q 2>&1 | tail -5
  期望：collected > 100 items，无 exit code 4
  失败时：输出具体错误信息，不要继续

Step 0.3 — 验证服务可达
  docker compose exec backend python -c "import httpx; r = httpx.get('http://localhost:8000/docs'); print(r.status_code)"
  期望：200
  失败时：输出 "Backend 未就绪。运行：docker compose up -d backend"
```

## Phase 1: Unit Tests

```
docker compose exec backend python -m pytest tests/unit/ -v --tb=short 2>&1
```

记录：passed / failed / errors 数量，每个失败测试的完整 traceback。

## Phase 2: Integration Tests

```
docker compose exec backend python -m pytest tests/integration/ -v --tb=short 2>&1
```

记录：passed / failed / errors 数量，每个失败测试的完整 traceback。

## Phase 3: E2E Tests

```
docker compose exec backend python -m pytest tests/e2e/ -v --tb=short 2>&1
```

如果 exit code = 4（未收集到测试）：回到 Phase 0 Step 0.1 检查是否为镜像过期问题。

## Phase 4: API Acceptance

使用容器内 Python httpx 替代 curl（自动处理 auth token）。先调用 login 获取 token，再逐个检查端点。

```
docker compose exec backend python -c "
import asyncio, httpx

async def check():
    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        # 1. 登录获取 token
        login_resp = await client.post('/api/v1/auth/login', json={
            'username': 'admin', 'password': 'admin123'
        }, headers={'X-Tenant': 'scnu'})
        if login_resp.status_code != 200:
            print(f'LOGIN FAILED: {login_resp.status_code} {login_resp.text[:200]}')
            return
        token = login_resp.json().get('access_token', '')

        headers = {'X-Tenant': 'scnu', 'Authorization': f'Bearer {token}'}

        # 2. 逐个检查 analytics 端点
        endpoints = [
            '/api/v1/admin/analytics/topic-cloud?days=30',
            '/api/v1/admin/analytics/emotion-timeline?days=30',
            '/api/v1/admin/analytics/hot-questions?days=30',
        ]
        for path in endpoints:
            resp = await client.get(path, headers=headers)
            print(f'{resp.status_code} {path}')

        # 3. 检查 knowledge index（无需 auth）
        resp = await client.get('/api/v1/admin/knowledge/index-status', headers={'X-Tenant': 'scnu'})
        print(f'{resp.status_code} /api/v1/admin/knowledge/index-status')
        data = resp.json()
        print(f'total_docs={data.get(\"total_docs\")} indexed_docs={data.get(\"indexed_docs\")}')

asyncio.run(check())
"
```

## 输出格式

写入 `reports/data-pipeline-test-results.md`，按以下结构：

```markdown
# Data Pipeline Test Results

**Date**: <YYYY-MM-DD>
**Branch**: <git branch>

## Phase 0: Environment Check
| Step | Status | Detail |
|------|--------|--------|
| 0.1 Test dirs exist | PASS/FAIL | <具体路径> |
| 0.2 Test collection | PASS/FAIL | <collected N items> |
| 0.3 Backend reachable | PASS/FAIL | <status code> |

## Phase 1: Unit Tests
| Result | Count |
|--------|-------|
| Passed | N |
| Failed | N |
| Errors | N |

### Failure Details
| Test | Failure Type | Error Summary |
|------|-------------|---------------|
| path::test_name | CODE / TEST / INFRA | <一句话摘要> |

## Phase 2: Integration Tests
(同上格式)

## Phase 3: E2E Tests
(同上格式)

## Phase 4: API Acceptance
| Endpoint | HTTP Status | Notes |
|----------|-------------|-------|
| GET /api/v1/admin/analytics/topic-cloud | 200 | <notes> |
| ... | ... | ... |

## Summary
| Phase | Status |
|-------|--------|
| Env Check | PASS/FAIL |
| Unit Tests | PASS/FAIL |
| Integration Tests | PASS/FAIL |
| E2E Tests | PASS/FAIL |
| API Acceptance | PASS/FAIL |
```

## Failure Type 分类规则

| 类型 | 判定标准 | 修复方向 |
|------|---------|---------|
| CODE | 业务逻辑错误、API 返回非预期值、数据不一致 | 修改业务代码 |
| TEST | Mock 设置错误、断言过时、fixture 问题、测试依赖不满足 | 修改测试代码 |
| INFRA | 容器不可达、目录缺失、权限问题、数据库连接失败 | 修改 Docker/配置/权限 |

每个失败必须标注一个类型。不确定时标注 UNKNOWN 并说明原因。

## 规则

1. Phase 0 任一 Step 失败 → 输出修复指令，终止后续阶段
2. 所有阶段必须执行（不因单个阶段失败而跳过后续阶段）
3. 每个失败必须标注 Failure Type
4. 不要修改任何测试或代码文件——仅记录和分类失败
5. 报告不超过 80 行，超出部分用摘要替代
