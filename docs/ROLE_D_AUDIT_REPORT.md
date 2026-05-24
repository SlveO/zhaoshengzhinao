# 角色 D — 数据 + 基础设施 问题审计报告

**生成日期：** 2026-05-23  
**审计范围：** scrapers/ · scripts/ · docker/ · data/ · docs/ · CI/CD · 测试 · 知识索引管道  
**严重程度定义：** 🔴 严重 → 🟠 高 → 🟡 中 → ⚪ 低

---

## 目录

1. [爬虫 (scrapers/)](#1-爬虫-scrapers)
2. [脚本 (scripts/)](#2-脚本-scripts)
3. [Docker 与 CI/CD](#3-docker-与-cicd)
4. [数据目录 (data/)](#4-数据目录-data)
5. [文档 (docs/)](#5-文档-docs)
6. [测试 (backend/tests/)](#6-测试-backendtests)
7. [知识索引管道](#7-知识索引管道)
8. [按优先级排序的汇总](#8-按优先级排序的汇总)

---

## 1. 爬虫 (scrapers/)

### 🔴 严重

| # | 问题 | 位置 |
|---|------|------|
| 1.1 | 三个 SCNU 爬虫共享相同的配置名称 `"scnu"`，导致它们都写入 `data/raw/scnu/`，共享日志文件和日志处理器。每个 `close()` 只移除自己的处理器，留下悬挂的处理器。 | `sources/scnu_admissions.py:37` `sources/scnu_curriculum.py:165` `sources/scnu_employment.py:202` |
| 1.2 | `run_all.py` 仅运行 7 个爬虫中的 3 个（`GaokaoScoreScraper`、`UniversityReportScraper`、`IndustryDataBuilder`）。其余 4 个爬虫（`SunshineGaokaoScraper`、`SCNUAdmissionsScraper`、`SCNUCurriculumScraper`、`SCNUEmploymentScraper`）有 `__main__` 块但无法通过编排器访问。 | `run_all.py:34-38` |

### 🟠 高

| # | 问题 | 位置 |
|---|------|------|
| 1.3 | `eol_api.py` 和 `scnu_admissions.py` 大量重复了 HTTP 客户端设置、响应解析和 `_parse_int` 逻辑（约 120 行）。对 API 的 Bug 修复必须应用于两处。 | `sources/eol_api.py:74-134` `sources/scnu_admissions.py:42-102` |
| 1.4 | `scripts/collect_provinces.py` 实现了自己的 HTTP 池化、限流和 JSON 解析，完全重复了 `BaseScraper` + `GaokaoScoreScraper` 逻辑，未从 `scrapers/` 导入任何内容。对 API 的 Bug 修复必须应用于两处。 | `scripts/collect_provinces.py` |
| 1.5 | 设计规范引用了 4 个不存在的文件：`sources/gd_eea.py`、`parsers/html_parser.py`、`parsers/data_cleaner.py`、`manual_import.py`。此外，`data/schema/` 为空（仅含 `.gitkeep`）。 | `docs/superpowers/specs/2026-05-14-gaokao-data-expansion-design.md:31-43` |

### 🟡 中

| # | 问题 | 位置 |
|---|------|------|
| 1.6 | `KNOWN_REPORT_URLS` 是猜测的占位符 URL，格式为 `{career-center}/report/2024.pdf`。每年的 URL 也不相同，但年份从未替换到 URL 模板中。 | `sources/university_reports.py:19-26` |
| 1.7 | `scnu_employment.py` 在运行时动态导入 `scnu_curriculum.py`（`from scrapers.sources.scnu_curriculum import SCNU_MAJORS`）— 存在未声明的硬依赖。 | `sources/scnu_employment.py:305-318` |
| 1.8 | 使用 `dir()` 的脆弱变量存在性检查：`college_hits if 'college_hits' in dir() else 0`。 | `sources/scnu_curriculum.py:303` |
| 1.9 | `run_all.py` 中未使用的变量 `code_to_pid`。 | `run_all.py:68-70` |

### ⚪ 低

| # | 问题 |
|---|------|
| 1.10 | 目标年份包括 2025 — 可能在数据不可用时静默产生空结果。 |
| 1.11 | `scrapers/requirements.txt` 和 `backend/requirements.txt` 各自独立维护，共享依赖项存在版本漂移风险。 |
| 1.12 | `scrapers/config.py` 和 `backend/config.py` 是不相关的配置，只是恰好同名。 |
| 1.13 | 任何爬虫代码均无测试覆盖。 |
| 1.14 | `data/raw/` 包含多次历史运行和不同命名规范的输出（`gaokao_scores/` vs `eol_api/`）。 |
| 1.15 | `scripts/collect_provinces.py` 的管道文档（DATA_GUIDE.md）引用的内容与 `scrapers/run_all.py` 不匹配。 |

---

## 2. 脚本 (scripts/)

### 🔴 严重 — 脚本已损坏

| # | 问题 | 位置 |
|---|------|------|
| 2.1 | `run_dev.sh` 引用了不存在的 `frontend/` 目录（实际目录为 `admin-spa/` 和 `mini-app/`）。`cd frontend` 将失败。此外，uvicorn 标志 `--reload` 存在拼写错误（应为 `--reload`）。 | `run_dev.sh:5` |
| 2.2 | `smoke_test.py` 导入了 `websockets`，但该 Python 包未安装。将抛出 `ModuleNotFoundError`。 | `smoke_test.py:54` |
| 2.3 | `capture_screenshots.py` 导入了 `playwright`，但该包和浏览器二进制文件均未安装。 | `capture_screenshots.py:6` |
| 2.4 | `verify_scnu_data.py` 的导入路径已损坏：`from backend.knowledge.client import get_chroma_client` 解析为 `backend/backend/knowledge/client.py`，因为脚本执行了 `os.chdir(_backend_dir)`。ChromaDB 验证步骤永久性失效。 | `verify_scnu_data.py:54` |

### 🟠 高 — 设计缺陷

| # | 问题 | 位置 |
|---|------|------|
| 2.5 | `seed_db.py` 删除 `users`、`user_profiles` 和 `recommendations`，但仅重新填充 `colleges` 和 `admission_data`。对已填充的数据库运行此脚本将静默销毁所有用户账户。 | `seed_db.py:107-110` |
| 2.6 | `seed_conversations.py` 在 `text()` SQL 中使用 f-string 插值（`f"SELECT id FROM tenants WHERE slug='{TENANT_SLUG}'"`）— 存在 SQL 注入模式。 | `seed_conversations.py:54` |
| 2.7 | `import_scnu_data.py` 和 `import_scnu_knowledge.py` 每条记录执行两次 `await db.commit()`。对于数百条记录，这将极其缓慢。 | `import_scnu_data.py:66-71` `import_scnu_knowledge.py:87-91` |

### 🟡 中 — 脆弱性

| # | 问题 | 位置 |
|---|------|------|
| 2.8 | `index_chroma.py` 没有 `sys.path` 设置 — 仅在从项目根目录运行时有效。 | `index_chroma.py:5-10` |
| 2.9 | `monitor_chroma.py` 硬编码了 ChromaDB 路径和集合名称 — 可能会与 `config.py` 的默认值产生偏差。 | `monitor_chroma.py:6,12` |
| 2.10 | `import_scnu_knowledge.py` 使用脆弱的 `__import__("knowledge.client", fromlist=[...])` 来延迟加载。 | `import_scnu_knowledge.py:48` |
| 2.11 | `capture_screenshots.py` 使用硬编码的 5 秒 `wait_for_timeout()` 等待 AI 响应，而不是等待 DOM 元素。 | `capture_screenshots.py:139,154` |
| 2.12 | `capture_screenshots.py` 如果登录返回 401，则继续执行且 token 为 `None` — 所有受保护的页面将渲染 401 错误。 | `capture_screenshots.py:20-38` |

### ⚪ 低

| # | 问题 |
|---|------|
| 2.13 | `smoke_test.py` 在 `async def run()` 内部使用同步的 `urllib.request.urlopen()` — 阻塞事件循环。 |
| 2.14 | `seed_db.py` 的 `data_dir` 相对于 CWD — 从其他目录运行时将失败。 |
| 2.15 | 12 个脚本中有 6 种不同的路径管理方法。没有统一的做法。 |

---

## 3. Docker 与 CI/CD

### 🔴 严重

| # | 问题 | 位置 |
|---|------|------|
| 3.1 | **前端 CI：** mini-app 的矩阵构建运行 `npm run build`，但 `mini-app/package.json` 没有 `build` 脚本。应使用 `npm run build:h5`（如 docker-compose.yml 中的正确配置）。CI 在 push 时**将失败**。 | `.github/workflows/frontend-ci.yml:31` |
| 3.2 | **关键文件未提交：** `docker-compose.yml`（在 `9cd5c55` 中从 git 跟踪中移除）、`docker-compose.prod.yml`、`.dockerignore`、`docker/static.conf`、所有 3 个 `.github/workflows/*.yml`、`.pre-commit-config.yaml`。CI 永远不会运行。协作者无法启动 Docker。Docker 构建在缺少 `static.conf` 时失败。 | 多个文件 |

### 🟡 中

| # | 问题 | 位置 |
|---|------|------|
| 3.3 | `admin-spa` 和 `mini-app` 服务没有 `healthcheck`。Nginx 的 `depends_on` 使用短格式（`service_started`），因此 nginx 可能在它们准备好之前启动，导致 502 错误。 | `docker-compose.yml:49-78` |
| 3.4 | Content-Security-Policy 允许来自任何来源的 `http:` 和 `https:`，以及 `'unsafe-inline'` 和 `'unsafe-eval'`。在生产环境中不提供任何保护。 | `docker/nginx.conf:30` |

### ⚪ 低

| # | 问题 |
|---|------|
| 3.5 | `docker/static.conf` 缺少安全头（在正常运行中由主 nginx 代理覆盖）。 |
| 3.6 | Lint CI 仅 lint `admin-spa`；`mini-app` 从未被 lint（也没有 lint 脚本）。 |
| 3.7 | 后端 CI 未设置 `DATA_DIR`；种子数据的回退路径解析为 `backend/data/seed/`，但该目录不存在。 |
| 3.8 | `config.py` 的 `DEEPSEEK_MODEL` 默认值为 `deepseek-v4-flash`，但 docker-compose 覆盖为 `deepseek-chat` — 不一致。 |
| 3.9 | `.dockerignore` 未排除 `backend/tests/` — 测试文件不必要地被复制到镜像中。 |
| 3.10 | `docker-compose.prod.yml` 仅为后端设置了 `deploy.resources.limits`；db、redis 和 nginx 均未设置。 |

---

## 4. 数据目录 (data/)

### 🔴 严重

| # | 问题 | 位置 |
|---|------|------|
| 4.1 | seed 和 approved 之间的数据量不匹配：`seed/scores.json` 有 194,041 条记录（31 个省份，96 所高校），但 `approved/admissions.json` 只有 29,749 条记录（仅广东）。一个 `export_full_data()` 管道无法同时产生这两个结果 — 种子文件在管道运行后被手动替换，或者使用了两个完全不同的管道运行。 | `data/seed/scores.json` vs `data/approved/admissions.json` |
| 4.2 | `data/cleaned/` 和 `data/processed/` 完全为空（仅含 `.gitkeep`）。管道声明了这些阶段，但没有代码向其中写入。 | `data/cleaned/` `data/processed/` |

### 🟠 高

| # | 问题 | 位置 |
|---|------|------|
| 4.3 | `data/raw/sunshine_gaokao/scraper.log` 与 `data/raw/eol_api/scraper.log` **完全相同**（MD5: `92c92567...`）— 一个陈旧的副本。Sunshine 爬虫从未产生数据文件。 | `data/raw/sunshine_gaokao/` |
| 4.4 | `data/approved/employment.json` 和 `data/approved/majors.json` 是跟踪的空数组 `[]`。 | `data/approved/` |
| 4.5 | `data/approved/scnu_comprehensive_knowledge.json` **未被 git 跟踪**（于 2026-05-23 手动添加）。 | `data/approved/` |

### 🟡 中 / ⚪ 低

| # | 问题 |
|---|------|
| 4.6 | `data/raw/` 在 `.gitignore` 中，但仍有 40 多个文件被跟踪 — 关于应该提交什么内容存在混淆。 |
| 4.7 | `data/schema/` 为空且在任何 Python 代码中从未被引用。 |
| 4.8 | `data/logs/` 为空 — 所有爬虫日志都存在于各自的 `data/raw/*/scraper.log` 中。 |
| 4.9 | `data/raw/university_reports/employment.json` 是空数组 — 爬虫产生零条记录。 |
| 4.10 | `seed/scores.json` 中有 5,810 条记录（3.0%）的 `min_rank` 为 null。 |
| 4.11 | `raw/gaokao_scores/admissions.json` 中有 40.5% 的记录的 `plan_count` 为 null。 |

---

## 5. 文档 (docs/)

### 🔴 严重 — 具有误导性或不可用

| # | 问题 | 位置 |
|---|------|------|
| 5.1 | 分支 `main` 和 `develop` 在多个文件中被引用但**不存在**。CI 工作流会在不存在 `develop` 分支事件时静默跳过。 | `README.md:107,139-141,163` `COLLABORATION.md:18-20,43-45,94` `.github/workflows/*.yml` |
| 5.2 | COLLABORATION.md 引用了 9 个不存在的 `SESSION_*.md` 文件，并指示每个开发者读取这些文件。多会话工作流完全无法执行。 | `COLLABORATION.md:57-66,76-83,92,104` |
| 5.3 | README 的目录树显示 `backend/data_pipeline/`，但该目录不存在。实际的导入脚本位于 `scripts/`，管道代码位于 `scrapers/storage/`。 | `README.md:73` |

### 🟠 高

| # | 问题 | 位置 |
|---|------|------|
| 5.4 | README 引用了 `OPENAI_API_KEY` 和 `SECRET_KEY` — 从未存在过。实际的变量名是 `DEEPSEEK_API_KEY` 和 `JWT_SECRET`。 | `README.md:35,202-203` |
| 5.5 | CONVENTIONS.md 列出了 5 个环境变量（`EMBEDDING_MODEL`、`CHROMA_PERSIST_DIR`、`FILE_STORE_DIR` 等），这些变量未出现在 `.env.example` 中。 | `CONVENTIONS.md:254-265` |
| 5.6 | `docs/modules/recommendation-module.md` 引用了不存在的 `frontend/` 路径（应为 `admin-spa/` 或 `mini-app/`）。 | 整个文档 |
| 5.7 | CONVENTIONS.md 的测试结构显示 `tests/unit/test_retriever.py`、`tests/integration/test_analytics_api.py`、`tests/fixtures/tenant_fixtures.py` — 这些均不存在。 | `CONVENTIONS.md:235-249` |
| 5.8 | COLLABORATION.md 使用旧的仓库根目录名称 `gaokao_agents/`；实际目录为 `zhaoshengzhinao`。 | `COLLABORATION.md:115` |

### 🟡 中

| # | 问题 |
|---|------|
| 5.9 | 8 个超能 spec/plan 文件包含数十条对不存在的 `frontend/` 目录的引用。 |
| 5.10 | 7 个文档仍引用 React 18；实际使用的版本是 React 19。 |
| 5.11 | PROJECT_MILESTONE.md 的数字已过时：提交次数 "20+" → 实际 148，管理员源文件 "17" → 实际 28，mini-app 文件 "19" → 实际 21，测试 "30+" → 实际 29。 |
| 5.12 | OPERATIONS.md 引用了不存在的 `backups/` 目录。 |
| 5.13 | DATA_GUIDE.md 章节编号错误（重复的章节 5）。 |
| 5.14 | ROLE_D_TECHNICAL_REFERENCE.md 声称有 10 个计划文档，实际为 6 个；声称有 12 个规范，实际为 13 个。 |
| 5.15 | `admin-spa/README.md` 是未修改的 Vite 脚手架默认 README — 零项目特定信息。 |
| 5.16 | DEPLOYMENT.md、OPERATIONS.md 和 ROLE_D_TECHNICAL_REFERENCE.md 是未跟踪的，且未从 README.md 链接。 |

### 文档空白

| # | 缺失的文档 |
|---|------|
| 5.17 | 无后端架构文档（API 约定、代理架构、服务层）。 |
| 5.18 | 无 Admin SPA 开发者指南（组件树、状态管理、路由）。 |
| 5.19 | 无 Mini-app 开发者指南（uni-app、Vue3、WebSocket 客户端）。 |
| 5.20 | 无数据库模式文档、无测试指南、无更新日志/发布说明。 |

---

## 6. 测试 (backend/tests/)

### 🔴 严重 — 测试无法运行

| # | 问题 | 位置 |
|---|------|------|
| 6.1 | **`asyncpg` 未安装在本地 Python 环境中。** 所有导入 `models` 的测试（直接或通过 `conftest.py`）在收集时失败，并抛出 `ModuleNotFoundError`。 | 本地 Python 环境 |
| 6.2 | `clean_db` 的 `autouse=True` 会为**每个**测试函数连接到 PostgreSQL，包括不需要数据库的纯单元测试（`test_b2b_prompt.py`、`test_guard.py`、`test_excel_validator.py` 等）。如果没有运行中的 PostgreSQL，整个测试套件无法启动。 | `tests/conftest.py:56-75` |
| 6.3 | 集成测试（`test_auth_api.py`、`test_chat_api.py`、`test_tenant_isolation.py`）需要运行中的 PostgreSQL **和** Redis。`test_chat_api.py` 在第 6 行未连接 Redis 时失败。 | `tests/integration/` |
| 6.4 | **`conftest.py` 未被跟踪。** 测试基础设施对所有协作者不可见。11 个未跟踪的测试文件（conftest + 3 个集成测试 + 7 个单元测试）其他任何人无法使用。 | `backend/tests/conftest.py` 及其他 |

### 🟠 高

| # | 问题 | 位置 |
|---|------|------|
| 6.5 | 遗留的 `tests/test_evidence_accumulator.py` 部分重复了 `tests/unit/test_evidence_accumulator.py`。根目录版本使用 `sys.path.insert` 和基于类的测试；单元版本使用 pytest 函数。 | 两个文件 |
| 6.6 | 所有 7 个分析测试使用脆弱的导入 `from tests.conftest import TEST_TENANT_ID`，这仅在 pytest 将项目根目录放在 `sys.path` 上时有效。 | `unit/test_analytics_*.py` |
| 6.7 | `test_evidence_accumulator.py` 中的死代码 `_add` 函数：从未被调用，并且存在 Bug（将 EvidenceAccumulator 对象作为维度字符串传递）。 | `unit/test_evidence_accumulator.py:14-16` |

### 🟡 中

| # | 问题 |
|---|------|
| 6.8 | `tenant_admin_user` 夹具在 `conftest.py` 中定义但从未被任何测试使用 — 死代码。 |
| 6.9 | `clean_db` 未清理表 `colleges`、`admission_data`、`industries`、`mappings` 或 `profiles` — 如果未来的测试写入这些表，数据将会泄漏。 |
| 6.10 | `GET /api/v1/admin/knowledge/documents` 没有 `get_current_tenant_user` 依赖 — 一个未经身份验证即可通过的端点（测试正确通过，但可能是安全漏洞）。 |

### ⚪ 低

| # | 问题 |
|---|------|
| 6.11 | profile、college、industry、compare、analytics router 或 tenants router 没有 API 路由测试。 |
| 6.12 | 遗留的 `test_evidence_accumulator.py` 和 `test_profile_analyzer.py` 使用 `sys.path.insert` 而不是正确的包导入。 |
| 6.13 | 缺少 `analytics/__init__.py` — 虽然可以工作（隐式命名空间包），但不合惯例。 |
| 6.14 | 在 `test_chat_service.py`（`FakeRedis`）、`test_excel_importer.py` 和 `test_admin_knowledge.py` 中有良好的 mock 模式 — 这些应该成为其他测试的模板。 |

---

## 7. 知识索引管道

### 🔴 严重 — 搜索已损坏

| # | 问题 | 位置 |
|---|------|------|
| 7.1 | **租户集合使用错误的嵌入模型进行索引。** `index_tenant_data()` 未将 `embeddings` 传递给 `collection.add()`。ChromaDB 默认使用 `all-MiniLM-L6-v2`（英文，384维），而预期的模型是 `BAAI/bge-large-zh-v1.5`（中文，1024维）。租户集合的语义搜索基本无效。 | `knowledge/indexer.py:105-109` |
| 7.2 | **模型下载在 Docker 中失败。** `MODELSCOPE_CACHE` 默认路径为 `/root/.cache/modelscope`，但 Dockerfile 切换到对 `/root/` 无写权限的用户 `app`。Docker 首次启动时抛出 `PermissionError`。HuggingFace 回退在中国超时。 | `knowledge_base/embeddings.py:9-10` `docker/Dockerfile.backend:21` |
| 7.3 | **知识搜索 API 对查询使用错误的嵌入函数。** `search_knowledge` 调用 `collection.query(query_texts=[q])`，使用默认的 ChromaDB 嵌入函数（MiniLM），而不是 `BAAI/bge-large-zh-v1.5`。即使文档使用正确的模型索引，查询结果也会不匹配。 | `api/routes/knowledge.py:28-31` |

### 🟠 高

| # | 问题 | 位置 |
|---|------|------|
| 7.4 | `TenantData.source_url` 从未传递到 ChromaDB 元数据。API 路由对所有结果返回 `source_url: ""`，无法追溯到源文档。 | `knowledge/indexer.py:97-103` `api/routes/knowledge.py:46-47` |
| 7.5 | `index_tenant_data()` 不在数据库记录上设置 `indexed_at`。调用者（`admin/router.py`、`excel_importer.py`）必须记住手动更新。任何省略此操作的未来调用者将破坏索引状态报告。 | `knowledge/indexer.py:90-109` |
| 7.6 | `trigger_reindex` 使用 `asyncio.create_task()` 进行即发即忘调用。无错误处理、无并发控制（两次触发 = 竞争条件）、无进度状态。 | `admin/router.py:153-161` |
| 7.7 | `upload_document` 使用裸的 `except Exception: pass` 吞噬所有索引错误。文档存在于 PostgreSQL 中但不可搜索 — 管理员用户永远不知道。 | `admin/router.py:106-111` |

### 🟡 中

| # | 问题 | 位置 |
|---|------|------|
| 7.8 | 知识搜索 API（`/api/v1/knowledge/search`）未被 `ModuleGateMiddleware` 限制。所有租户，无论层级如何，都可以访问 — 无法作为高级功能进行付费限制。 | `api/routes/knowledge.py:9` `core/module_registry.py:42-55` |
| 7.9 | `excel_importer.import_excel` 提交未能索引的文档；`imported` 计数包括未能索引的行 — 用户得到的数字具有误导性。 | `data/onboarding/excel_importer.py:78-84` |
| 7.10 | `TenantData.indexed_at` 默认为 `NULL`。无法区分"等待首次索引"和"索引失败"。 | `tenants/models.py:61` |
| 7.11 | API 使用 `client.get_collection()`（如果未找到则抛出异常），而索引器使用 `client.get_or_create_collection()` — 不一致的模式。 | `api/routes/knowledge.py:24` vs `knowledge/indexer.py:94` |
| 7.12 | 分数与距离的解释不同：`search_similar` 返回原始距离，API 路由返回 `1 - distance` — 同一结果的两个不同数字。 | `chroma_client.py:41` vs `api/routes/knowledge.py:45` |
| 7.13 | `recommendation/cross_college.py` 中的 `cross_college_recommendations` 被声明为 `async`，但只调用同步函数 — 具有误导性。 | `recommendation/cross_college.py:5-23` |

### ⚪ 低

| # | 问题 |
|---|------|
| 7.14 | `models/__init__.py` 中的 `init_db()` 不导入 `tenants.models` — 租户表不会由 `Base.metadata.create_all()` 创建。（如果正确配置，由 Docker CMD 中的 Alembic 缓解。） |
| 7.15 | `reindex_tenant` 是 `async`，但在 FastAPI 的异步上下文中同步调用 ChromaDB — 在重新索引期间阻塞事件循环。 |
| 7.16 | 两个不同的 `_sanitize_meta*` 函数具有不同的行为（一个转换为 JSON 字符串，另一个仅将 None 替换为 ""）。 |
| 7.17 | ChromaDB 客户端单例在模块导入时创建 — 在设置被 mock 的测试中会导致问题。 |
| 7.18 | HuggingFace 回退在 `SentenceTransformer()` 上没有超时 — 在中国可能会无限期挂起。 |
| 7.19 | ROLE_D_TECHNICAL_REFERENCE.md 错误地声称 `MODELSCOPE_CACHE` 有一个持久的 Docker 卷。（实际没有这样的卷存在。） |

---

## 8. 按优先级排序的汇总

### 立即操作（本周）

| 优先级 | 操作 | 涉及的问题 |
|--------|------|-------------|
| **P0** | 提交所有未跟踪的关键文件：`docker-compose.yml`、`.github/workflows/`、`.dockerignore`、`docker/static.conf`、`.pre-commit-config.yaml`、`backend/tests/conftest.py` 及所有未跟踪的测试文件 | 3.2, 6.4 |
| **P0** | 修复 ChromaDB 嵌入不匹配：向 `index_tenant_data()` 添加显式的 `embeddings` 参数，向知识搜索 API 查询添加 `query_embeddings` | 7.1, 7.3 |
| **P0** | 修复 Docker 中的模型下载：在 docker-compose 中设置 `MODELSCOPE_CACHE` 环境变量并挂载卷；或在下载前 chown 缓存目录 | 7.2 |
| **P1** | 修复前端 CI：为 mini-app 矩阵作业添加条件 `npm run build:h5` | 3.1 |
| **P1** | 修复 `run_all.py` 以包含所有 7 个爬虫（或记录独立的爬虫） | 1.2 |
| **P1** | 修复 `run_dev.sh`：将 `frontend` 替换为 `admin-spa`，将 `--reload` 替换为 `--reload` | 2.1 |

### 短期（1-2 周内）

| 优先级 | 操作 | 涉及的问题 |
|--------|------|-------------|
| **P2** | 修复 SCNU 爬虫配置名称冲突（为每个爬虫指定不同的名称） | 1.1 |
| **P2** | 重构 `eol_api.py` 和 `scnu_admissions.py` 中的重复解析/HTTP 逻辑 | 1.3, 1.4 |
| **P2** | 更新 `.env.example` 以包含 `config.py` 中的所有 15 个设置 | 5.4, 5.5 |
| **P2** | 在 `seed_db.py` 中添加保护措施：在删除表之前要求 `--force` 标志 | 2.5 |
| **P2** | 向 `MONGO_URL` 模式添加 SQL 参数绑定（将 f-string 替换为 `:slug`） | 2.6 |
| **P2** | 向 `admin-spa` 和 `mini-app` Docker 服务添加健康检查 | 3.3 |

### 中期（本月内）

| 优先级 | 操作 | 涉及的问题 |
|--------|------|-------------|
| **P3** | 修复 `verify_scnu_data.py` 导入路径 | 2.4 |
| **P3** | 合并 `import_scnu_data.py` 中的双重提交（每批提交一次） | 2.7 |
| **P3** | 更新 README 环境变量名称（`OPENAI_API_KEY` → `DEEPSEEK_API_KEY`） | 5.4 |
| **P3** | 修复 `index_tenant_data` 中缺失的 `source_url` — 传递给 ChromaDB 元数据 | 7.4 |
| **P3** | 向 `trigger_reindex` 添加错误处理和并发控制 | 7.6 |
| **P3** | 删除对不存在的 `frontend/` 目录的文档引用 | 5.6, 5.9 |
| **P3** | 删除遗留的重复测试文件（`tests/test_evidence_accumulator.py`） | 6.5 |

### 持续关注

| 优先级 | 操作 | 涉及的问题 |
|--------|------|-------------|
| **P4** | 添加爬虫测试（优先处理 `BaseScraper` 和 `_parse_int`） | 1.13 |
| **P4** | 标准化 12 个脚本的路径管理 — 使用统一的 `sys.path` 方法 | 2.15 |
| **P4** | 编写缺失的文档：数据库模式、测试指南、Admin SPA 开发者指南 | 5.17-5.20 |
| **P4** | 添加 API 路由测试：profile、college、industry、compare、analytics、tenants | 6.11 |
| **P4** | 限制知识搜索 API 并添加模块门控 | 7.8 |
| **P4** | 将 `MODULE_DEPENDENCIES` 和 `MODULE_ROUTE_MAP` 添加到模块注册表文档 | — |

---

## 统计

| 类别 | 🔴 严重 | 🟠 高 | 🟡 中 | ⚪ 低 | 总计 |
|------|---------|------|------|------|------|
| 爬虫 | 2 | 3 | 4 | 6 | 15 |
| 脚本 | 4 | 3 | 5 | 3 | 15 |
| Docker / CI | 2 | 0 | 2 | 6 | 10 |
| 数据 | 2 | 3 | 6 | 0 | 11 |
| 文档 | 3 | 5 | 8 | 4 | 20 |
| 测试 | 4 | 3 | 3 | 4 | 14 |
| 索引管道 | 3 | 4 | 6 | 6 | 19 |
| **总计** | **20** | **21** | **34** | **29** | **104** |
