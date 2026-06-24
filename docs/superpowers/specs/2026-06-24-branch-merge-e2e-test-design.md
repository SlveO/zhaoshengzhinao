# 分支合并与端到端测试设计

> 创建日期：2026-06-24
> 范围：Module A（PR #6 知识库爬虫）+ Module B（feat/module-b-ai-consulting-system AI 咨询系统）
> 目标：合并两个分支到 main，重写全部测试，Docker 全栈验证，提供本地体验链接

---

## 1. 背景与范围

### 1.1 待合并分支

| 分支 | 贡献者 | 规模 | 内容 |
|------|--------|------|------|
| `bigteacher/feat/knowledge-base`（PR #6） | bigteacher-bit | 5 文件 +388 行 | SCNU 官方录取数据 PDF 爬虫 + 本地开发环境配置 |
| `origin/feat/module-b-ai-consulting-system` | azhe-fole | 17 文件 +6649 行 | C-end 画像提取 + profile_bridge + 准确率基准 + 测试 |

### 1.2 不在范围内

- Module C（数据闭环）：无代码实现，本次不处理
- Module B3（交互体验优化）：未实现，属 Phase 2
- 分支原有测试代码：全部丢弃（test_*.py），由独立子代理重写
- 基准数据集（knowledge_qa.json / profile_extraction.json）：保留，作为基准测试的 ground truth 输入
- 基准脚本（run_accuracy.py）：保留，子代理 C 直接运行

### 1.3 约束

- 合并目标：直接合并到 main（用户指定）
- 测试规范：遵循 `.claude/rules/testing.md` 的 HARD RULE
- 开发环境：本地 Docker（已启动），6 服务全栈
- 测试隔离：契约驱动黑盒测试，子代理不读实现代码

---

## 2. 整体流程架构

```
Phase 1: 预检与合并 Module A（PR #6）
  ├─ 1.1 语法预检：py_compile + tsc --noEmit
  ├─ 1.2 合并 bigteacher/feat/knowledge-base → main
  └─ 1.3 冒烟验证：Docker 启动 db+redis，运行爬虫导入知识库

Phase 2: 预检与合并 Module B
  ├─ 2.1 语法预检：py_compile 全量扫描 17 文件
  ├─ 2.2 合并 origin/feat/module-b-ai-consulting-system → main
  └─ 2.3 冲突检查：miniapp.py、topic_cloud.py 是修改文件，需人工确认

Phase 3a: 编写测试契约文档（5 份，基于需求规格，不读实现）
Phase 3b: 生成模块索引文档（仅公开接口签名）

Phase 4: 并行派发 3 个独立子代理重写测试
  ├─ 子代理 A：单元测试（独立上下文，读契约+接口签名）
  ├─ 子代理 B：集成测试（独立上下文）
  └─ 子代理 C：端到端测试（独立上下文，基于 Docker 全栈）

Phase 5: Docker 全栈验证
  ├─ 5.1 docker-compose up -d --build（6 服务）
  ├─ 5.2 运行单元 + 集成 + E2E 测试
  └─ 5.3 运行准确率基准测试（95% 阈值）

Phase 6: 提供本地体验链接
  ├─ 小程序：http://localhost/
  ├─ 管理后台：http://localhost/admin/
  └─ API 文档：http://localhost/api/docs
```

---

## 3. 模块索引文档结构（Phase 3b 产出）

合并完成后生成 `docs/MODULE_INDEX.md`，仅包含公开接口签名，不含实现细节。

### 3.1 Module A 索引

```
scrapers/sources/scnu_zsb_admissions.py
  class SCNUZsbAdmissionsScraper(BaseScraper)
    - 输入：HTML 页面 URL（广东/外省双表）
    - 输出：List[dict]（年份/省份/科类/批次/最低分/最低位次）
    - 依赖：pdfplumber, BeautifulSoup, base_scraper.BaseScraper

docker-compose.yml（修改）
  - 改动：暴露 db(5432) 和 redis(6379) 端口到宿主机

scrapers/base_scraper.py（修改）
  - 改动：tenacity 9.0 兼容性修复

backend/config.py（修改）
  - 改动：CORS 端口支持扩展
```

### 3.2 Module B 索引

```
backend/services/cend_profile_analyzer.py（+486 行）
  class CendExtractionResult
    - 字段：basic, interests, concerns, riasec, values, region_pref, extra
  async analyze_cend_turn(user_text, history_text, existing_profile) -> CendExtractionResult
  build_cend_analysis_prompt(user_text, history_text, existing_summary) -> str
  parse_cend_response(text: str) -> CendExtractionResult
  merge_extraction_results(existing: dict, new: CendExtractionResult) -> dict
  _compute_completeness(result: CendExtractionResult) -> str  # "L1"|"L2"|"L3"

backend/services/profile_bridge.py（+321 行）
  async should_extract(session_id: str) -> bool
  async bridge_profile_to_session_profiles(session, tenant_id, user_content, full_content) -> bool
  async load_existing_profile_json(session_id: str, tenant_id: str) -> Optional[dict]
  async get_chat_message_count(session_id: str) -> int

backend/api/routes/miniapp.py（修改，+14 行）
  - 集成点：SSE 响应完成后，每 3 轮调用 bridge_profile_to_session_profiles()
  - 容错：bridge 失败不阻塞 SSE，仅 warning 日志

backend/analytics/topic_cloud.py（修改，+13 行）
  - 新增数据源：session_profiles.profile_json.concerns（权重 x2）

backend/agents/conversation/prompts_b2b.py（修改，+4 行）
  - B2B prompt 微调
```

---

## 4. 测试契约文档（Phase 3a 产出）

### 4.1 契约编写原则

- 基于需求规格（执行计划 B1 + PR #6 描述），不读实现代码
- 只描述行为预期（"做什么"），不包含实现细节（"怎么做"）
- 包含：公开接口签名 + 行为契约 + 边界条件

### 4.2 契约文档清单

| 契约文档 | 基于需求来源 | 覆盖模块 |
|----------|------------|----------|
| `contracts/scnu_scraper_contract.md` | PR #6 描述 + 爬虫需求 | SCNUZsbAdmissionsScraper |
| `contracts/cend_profile_analyzer_contract.md` | 执行计划 B1 字段体系 | cend_profile_analyzer 全部函数 |
| `contracts/profile_bridge_contract.md` | 执行计划 B1 桥接逻辑 | profile_bridge 全部函数 |
| `contracts/miniapp_sse_contract.md` | 执行计划 B1 SSE 集成 | miniapp.py 对话端点 + bridge 触发 |
| `contracts/analytics_consumption_contract.md` | 执行计划 B1 看板通路 | topic_cloud + profile_dashboard 数据消费 |

### 4.3 契约文档示例结构

```markdown
# 测试契约：cend_profile_analyzer

## 公开接口（仅签名，无函数体）
- async analyze_cend_turn(user_text, history_text, existing_profile) -> CendExtractionResult
- parse_cend_response(text: str) -> CendExtractionResult
- merge_extraction_results(existing, new) -> dict
- _compute_completeness(result) -> str  # "L1" | "L2" | "L3"

## 行为契约

### analyze_cend_turn
- 输入：用户消息文本 + 对话历史 + 已有画像（可空）
- 输出：CendExtractionResult，含 7 字段
- 契约 1：LLM 返回合法 JSON → 返回结构化结果
- 契约 2：LLM 返回非法 JSON → 返回空结果（不抛异常）
- 契约 3：LLM 超时/失败 → 返回空结果（不抛异常）
- 契约 4：existing_profile 非空 → 新提取与已有信息合并

### _compute_completeness
- 契约 1：仅 basic → "L1"
- 契约 2：basic + interests + concerns → "L2"
- 契约 3：basic + interests + concerns + riasec + values → "L3"
- 契约 4：所有字段空 → "L1"

## 边界条件
- 空字符串、超长输入（>10000 字符）、纯标点、多语言混合
- existing_profile 为 None / 空字典 / 部分填充
```

---

## 5. 测试范围 — 基于模块完整功能

### 5.1 Module A 测试范围

| 测试层 | 覆盖范围 |
|--------|----------|
| 单元测试 | `SCNUZsbAdmissionsScraper` 全部方法：PDF URL 提取、表格解析（广东/外省双格式）、数据清洗、异常处理 |
| 单元测试 | `BaseScraper` 基类：tenacity 重试逻辑、请求封装 |
| 集成测试 | 爬虫 → 知识库索引完整链路：爬取 → ChromaDB 写入 → 检索 API 验证 |
| 集成测试 | 配置完整性：docker-compose 端口、CORS、config.py 加载 |

### 5.2 Module B 测试范围

| 测试层 | 覆盖范围 |
|--------|----------|
| 单元测试 | `cend_profile_analyzer` 全部函数：analyze_cend_turn（LLM mock）、prompt 构造、JSON 解析、深度合并、completeness 计算 |
| 单元测试 | `profile_bridge` 全部函数：3 轮触发逻辑、主桥接、画像读取、消息计数、JSON 备份、DB merge |
| 单元测试 | `topic_cloud` 完整功能：词频统计 + concerns 数据源 + 权重计算 + Top50 截断 |
| 集成测试 | SSE 对话完整链路：发消息 → LLM 响应 → 3 轮触发 bridge → session_profiles 写入 → JSON 备份 → SSE 含 profile_updated |
| 集成测试 | 画像存储与读取：首次创建 → 后续更新（merge）→ completeness 升级 → profile_dashboard 查询 |
| 集成测试 | 分析看板数据消费：topic_cloud 读 concerns → profile_dashboard 读 RIASEC → region_distribution 读地域 |
| 集成测试 | 容错与隔离：bridge 失败不阻塞 SSE、租户隔离、并发安全 |
| E2E 测试 | 用户完整旅程（Docker 全栈）：小程序对话 6 轮 → session_profiles 有记录 → 管理后台看板显示画像 |
| E2E 测试 | 管理后台完整流程：管理员登录 → 分析看板 → 数据来自真实对话非 mock |
| 基准测试 | 准确率验证：KB Q&A ≥95%、提取准确率 ≥95% |

### 5.3 子代理分工

| 子代理 | 职责 | 输入 | 输出 |
|--------|------|------|------|
| 子代理 A | 全部单元测试 | 契约文档 + 接口签名 | test_scnu_scraper.py、test_cend_profile_analyzer.py、test_profile_bridge.py、test_topic_cloud.py |
| 子代理 B | 全部集成测试 | 契约文档 + 接口签名 | test_scraper_pipeline.py、test_cend_data_pipeline.py、test_analytics_consumption.py |
| 子代理 C | E2E + 基准 | 契约文档 + Docker 全栈 | test_student_journey.py、test_admin_dashboard.py、运行 run_accuracy.py |

### 5.4 子代理输入与禁止项

| 项目 | 允许 | 禁止 |
|------|------|------|
| 测试契约文档 | ✅ 读取 | — |
| 公开接口签名 | ✅ 读取 | — |
| 模块索引文档 | ✅ 读取 | — |
| 执行计划 | ✅ 读取 | — |
| 实现代码函数体 | ❌ | 禁止读取 |
| 分支原有测试代码 | ❌ | 禁止读取 |
| 实现内部细节 | ❌ | 禁止读取 |

---

## 6. Docker 全栈验证

### 6.1 服务栈

| 服务 | 镜像 | 端口 | 用途 |
|------|------|------|------|
| db | postgres:16-alpine | 5432 | PostgreSQL |
| redis | redis:7-alpine | 6379 | 会话状态 + 限流 |
| backend | 自建 Dockerfile.backend | 8000（内部） | FastAPI + LangGraph + ChromaDB |
| admin-spa | 自建 Dockerfile.frontend | 80（内部） | 管理后台 |
| mini-app | 自建 Dockerfile.frontend | 80（内部） | 学生端小程序 |
| nginx | nginx:1.27-alpine | 80（宿主机） | 反向代理入口 |

### 6.2 验证流程

```
5.1 docker-compose up -d --build
5.2 后端启动自检：init_db → ensure_tenant → auto_import_knowledge → embedding 预热
5.3 运行测试（backend 容器内）：
    - pytest tests/unit/ -v
    - pytest tests/integration/ -v
    - pytest tests/e2e/ -v
    - python tests/benchmarks/run_accuracy.py
5.4 判定：全部通过 → 合并成功；准确率 <95% → warning；失败 → 回滚或修复
```

### 6.3 E2E 测试技术方案

| 项目 | 方案 |
|------|------|
| 测试框架 | Playwright（Python 版，容器内运行） |
| 浏览器 | Chromium（backend 容器内安装） |
| 访问入口 | 通过 nginx（http://nginx:80） |
| 测试数据 | 测试前注入种子对话，测试后清理 |
| 截图 | 失败时自动保存到 tests/e2e/screenshots/ |

---

## 7. 本地体验链接

测试通过后提供以下链接：

| 入口 | URL | 体验内容 |
|------|-----|----------|
| 学生端小程序 | http://localhost/ | 发送对话 → AI 咨询 → 6 轮后画像更新 |
| 管理后台 | http://localhost/admin/ | 登录 → 画像看板 → RIASEC/地域/词云 |
| API 文档 | http://localhost/api/docs | Swagger UI → 手动测试 API |
| 后端日志 | docker-compose logs -f backend | 实时查看 profile_bridge 日志 |

### 人工体验脚本

```
1. 打开 http://localhost/（小程序）
2. 发送 6 条对话消息（如"我是广东物理类考生，分数 580"）
3. 观察第 3、6 轮后 backend 日志出现 "Profile bridge" 字样
4. 打开 http://localhost/admin/（管理后台）
5. 登录后进入画像看板
6. 验证 RIASEC 雷达图、地域分布、话题词云有数据
7. 打开 http://localhost/api/docs
8. 调用 GET /api/v1/analytics/topic-cloud 验证 concerns 数据
```

---

## 8. 错误处理与回滚

### 8.1 合并阶段错误处理

| 阶段 | 错误类型 | 处理策略 |
|------|----------|----------|
| 语法预检 | py_compile 失败 | 立即停止，不合并；报告错误文件与行号 |
| 合并冲突 | git merge conflict | miniapp.py/topic_cloud.py 需人工解决；解决后重新预检 |
| import 错误 | 模块引用失败 | 检查依赖链，补全 __init__.py 或修复 import 路径 |
| Docker 构建 | 镜像构建错误 | 检查 requirements.txt 是否含 pdfplumber/BeautifulSoup |

### 8.2 测试阶段错误处理

| 场景 | 处理策略 |
|------|----------|
| 单元测试失败 | 子代理修复测试（不允许改实现）；确认实现 bug 则记录 issue |
| 集成测试失败 | 排查测试数据 vs 链路问题；检查 fixture 隔离 |
| E2E 测试失败 | 查看截图 + 容器日志；常见：服务未就绪、端口冲突 |
| 准确率 <95% | warning 不阻塞；记录到基准报告 |
| LLM 调用失败 | 单元/集成测试必须 mock LLM；仅基准测试用真实 LLM |

### 8.3 回滚策略

```
触发条件：
  - 语法预检失败且无法快速修复
  - 合并冲突无法解决
  - Docker 构建失败且依赖问题复杂
  - 单元测试失败率 > 30%

回滚操作：
  git reset --hard <pre-merge-commit>
  docker-compose down -v
  记录回滚原因到 docs/ROLLBACK_LOG.md
```

### 8.4 关键约束

1. 测试子代理不得修改实现代码
2. 实现 bug 由独立修复流程处理
3. 每个 Phase 完成后提交一次，便于按 Phase 回滚
4. Docker 卷隔离，测试后 `docker-compose down -v` 清理

---

## 9. 验证标准

| 检查项 | 方法 | 标准 |
|--------|------|------|
| 语法预检 | py_compile + tsc --noEmit | 0 errors |
| 单元测试 | pytest tests/unit/ -v | 100% pass |
| 集成测试 | pytest tests/integration/ -v | 100% pass |
| E2E 测试 | pytest tests/e2e/ -v | 100% pass |
| 准确率（KB） | run_accuracy.py | ≥95%（warning） |
| 准确率（提取） | run_accuracy.py | ≥95%（warning） |
| Docker 全栈 | docker-compose up -d | 6 服务健康 |
| 本地体验 | 浏览器访问 3 个链接 | 功能正常 |
