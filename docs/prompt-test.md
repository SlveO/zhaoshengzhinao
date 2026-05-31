# Prompt B: 执行 Data Pipeline 测试验证

## 目标

在修复后重新执行完整测试流水线，验证所有问题已解决，生成测试结果报告。

## 背景

修复内容见 @docs/prompt-fix.md（Task 1-3），修复前基线见 @reports/data-pipeline-test-results.md。

修复前状态：
- 单元测试 134/135（1 个 mock 缺陷导致失败）
- E2E 测试未执行（镜像过期，exit code 4）
- API 验收全部 200

## 可用工具

- **Bash**：执行 `docker compose exec` 命令
- **Agent (test-runner)**：执行 pytest 并返回压缩结果，避免上下文膨胀
- **Agent (cmd-executor)**：执行长时间命令（docker compose build 等）

## Phase 0: 环境检查

执行测试前必须完成以下检查。任一步骤失败 → 输出修复指令并终止。

```
Step 0.1 — 验证测试目录在容器中存在
  docker compose exec backend ls tests/unit/ tests/integration/ tests/e2e/
  期望：三个目录均列出文件列表
  失败时：运行 docker compose build backend && docker compose up -d backend，然后重试

Step 0.2 — 验证测试可被收集
  docker compose exec backend python -m pytest tests/ --collect-only -q 2>&1 | tail -3
  期望：collected > 100 items

Step 0.3 — 验证服务可达
  docker compose exec backend python -c "import httpx; print(httpx.get('http://localhost:8000/docs').status_code)"
  期望：200
```

## Phase 1: Unit Tests

委托 `test-runner` agent 执行：

```
docker compose exec backend python -m pytest tests/unit/ -v --tb=short 2>&1
```

统计 passed / failed / errors。每个失败记录完整 traceback + 对应的源文件行号。

## Phase 2: Integration Tests

```
docker compose exec backend python -m pytest tests/integration/ -v --tb=short 2>&1
```

## Phase 3: E2E Tests

```
docker compose exec backend python -m pytest tests/e2e/ -v --tb=short 2>&1
```

如果 exit code = 4（未收集到测试）：确认 Phase 0 Step 0.1 已通过。如仍失败，检查镜像是否重建。

## Phase 4: API Acceptance

容器内 Python 脚本（替代 curl，自动处理 auth token）：

```
docker compose exec backend python -c "
import asyncio, httpx

async def check():
    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        # 登录
        login_resp = await client.post('/api/v1/auth/login', json={
            'username': 'admin', 'password': 'admin123'
        }, headers={'X-Tenant': 'scnu'})
        token = login_resp.json().get('access_token', '')
        headers = {'X-Tenant': 'scnu', 'Authorization': f'Bearer {token}'}

        endpoints = [
            '/api/v1/admin/analytics/topic-cloud?days=30',
            '/api/v1/admin/analytics/emotion-timeline?days=30',
            '/api/v1/admin/analytics/hot-questions?days=30',
        ]
        for path in endpoints:
            r = await client.get(path, headers=headers)
            print(f'{r.status_code} {path}')

        r = await client.get('/api/v1/admin/knowledge/index-status', headers={'X-Tenant': 'scnu'})
        data = r.json()
        print(f'{r.status_code} /api/v1/admin/knowledge/index-status')
        print(f'total_docs={data.get(\"total_docs\")} indexed_docs={data.get(\"indexed_docs\")}')

asyncio.run(check())
"
```

## 输出格式

写入 @reports/data-pipeline-test-results.md，覆盖旧报告。结构：

```markdown
# Data Pipeline Test Results

**Date**: <YYYY-MM-DD>
**Branch**: <git branch>

## Phase 0: Environment Check
| Step | Status | Detail |
|------|--------|--------|
| 0.1 Test dirs exist | PASS/FAIL | <路径> |
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
| path::name | CODE / TEST / INFRA | <摘要> |

## Phase 2-4: (同上格式，Phase 4 用端点表格)

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
| CODE | 业务逻辑错误、API 返回非预期值 | 修改业务代码 |
| TEST | Mock 设置错误、断言过时、fixture 问题 | 修改测试代码 |
| INFRA | 容器不可达、目录缺失、权限、DB 连接 | 修改 Docker/配置 |

## 规则

1. **DO NOT modify any test or code file** —— 仅记录和分类失败，不做修改
2. Phase 0 任一 Step 失败 → 输出修复指令，终止后续阶段
3. 各阶段独立执行，不因一个阶段失败而跳过其他阶段
4. 每个失败必须标注 Failure Type（CODE / TEST / INFRA）
5. 报告不超过 80 行，超出部分用摘要
6. 所有测试命令通过 `docker compose exec backend` 在容器内执行
