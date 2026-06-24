# 分支合并与端到端测试实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Module A（PR #6 知识库爬虫）和 Module B（AI 咨询系统）合并到 main，重写全部测试，Docker 全栈验证，提供本地体验链接。

**Architecture:** 顺序合并 A→B 到 main，每步语法预检。合并后编写测试契约文档（黑盒规格），派发 3 个独立子代理并行重写单元/集成/E2E 测试。最终 Docker 6 服务全栈运行所有测试并提供本地体验链接。

**Tech Stack:** Python 3.11 / FastAPI / LangGraph / ChromaDB / Playwright / pytest / Docker Compose / PostgreSQL / Redis

**设计文档:** `docs/superpowers/specs/2026-06-24-branch-merge-e2e-test-design.md`

---

## 文件结构

### 合并阶段产出
- 修改: `backend/requirements.txt`（补全 pdfplumber、beautifulsoup4 依赖）
- 修改: `docker/Dockerfile.backend`（复制 scrapers/ 目录到容器）
- 修改: `docker-compose.yml`（挂载 scrapers/ 目录）
- 删除: `backend/tests/unit/test_cend_profile_analyzer.py`（分支原有，丢弃重写）
- 删除: `backend/tests/unit/test_profile_bridge.py`（分支原有，丢弃重写）
- 删除: `backend/tests/integration/test_cend_data_pipeline.py`（分支原有，丢弃重写）

### 契约文档产出（Phase 3a）
- 创建: `docs/contracts/scnu_scraper_contract.md`
- 创建: `docs/contracts/cend_profile_analyzer_contract.md`
- 创建: `docs/contracts/profile_bridge_contract.md`
- 创建: `docs/contracts/miniapp_sse_contract.md`
- 创建: `docs/contracts/analytics_consumption_contract.md`

### 索引文档产出（Phase 3b）
- 创建: `docs/MODULE_INDEX.md`

### 测试产出（Phase 4，子代理编写）
- 创建: `backend/tests/unit/test_scnu_scraper.py`（子代理 A）
- 创建: `backend/tests/unit/test_cend_profile_analyzer.py`（子代理 A，重写）
- 创建: `backend/tests/unit/test_profile_bridge.py`（子代理 A，重写）
- 创建: `backend/tests/unit/test_topic_cloud.py`（子代理 A）
- 创建: `backend/tests/integration/test_scraper_pipeline.py`（子代理 B）
- 创建: `backend/tests/integration/test_cend_data_pipeline.py`（子代理 B，重写）
- 创建: `backend/tests/integration/test_analytics_consumption.py`（子代理 B）
- 创建: `backend/tests/e2e/test_student_journey.py`（子代理 C，重写）
- 创建: `backend/tests/e2e/test_admin_dashboard.py`（子代理 C，重写）

### 保留的分支文件
- 保留: `backend/tests/benchmarks/knowledge_qa.json`（ground truth 数据集）
- 保留: `backend/tests/benchmarks/profile_extraction.json`（ground truth 数据集）
- 保留: `backend/tests/benchmarks/run_accuracy.py`（基准脚本）

---

## Phase 1: 预检与合并 Module A（PR #6）

### Task 1: Module A 语法预检

**Files:**
- Read: `scrapers/sources/scnu_zsb_admissions.py`（在 bigteacher/feat/knowledge-base 分支）
- Read: `scrapers/base_scraper.py`（在 bigteacher/feat/knowledge-base 分支）
- Read: `backend/config.py`（在 bigteacher/feat/knowledge-base 分支）

- [ ] **Step 1: Fetch bigteacher 远程分支**

```bash
git fetch bigteacher feat/knowledge-base
```

Expected: 无错误输出

- [ ] **Step 2: 语法预检所有改动文件**

```bash
git show bigteacher/feat/knowledge-base:scrapers/sources/scnu_zsb_admissions.py > /tmp/scnu_scraper.py
git show bigteacher/feat/knowledge-base:scrapers/base_scraper.py > /tmp/base_scraper.py
git show bigteacher/feat/knowledge-base:backend/config.py > /tmp/config.py
python -m py_compile /tmp/scnu_scraper.py /tmp/base_scraper.py /tmp/config.py
```

Expected: 无输出（py_compile 成功），exit code 0

- [ ] **Step 3: 检查 import 依赖完整性**

```bash
git show bigteacher/feat/knowledge-base:scrapers/sources/scnu_zsb_admissions.py | Select-String "^import |^from "
```

Expected: 确认 import 的 pdfplumber、bs4、tenacity 在 scrapers/requirements.txt 中存在

---

### Task 2: 合并 Module A 到 main

**Files:**
- Modify: `scrapers/sources/scnu_zsb_admissions.py`（新增）
- Modify: `scrapers/base_scraper.py`（修改）
- Modify: `backend/config.py`（修改）
- Modify: `docker-compose.yml`（修改）

- [ ] **Step 1: 确认当前在 main 分支且工作区干净**

```bash
git checkout main
git status
```

Expected: `nothing to commit, working tree clean`

- [ ] **Step 2: 记录合并前 commit hash**

```bash
git rev-parse HEAD
```

Expected: 输出 40 字符 hash，记录此值作为 `PRE_MERGE_A_COMMIT`，用于回滚

- [ ] **Step 3: 合并 Module A 分支**

```bash
git merge bigteacher/feat/knowledge-base --no-edit
```

Expected: 合并成功，无冲突（Module A 改动的文件与 main 无重叠）

- [ ] **Step 4: 合并后语法预检**

```bash
python -m py_compile scrapers/sources/scnu_zsb_admissions.py scrapers/base_scraper.py backend/config.py
```

Expected: 无输出，exit code 0

- [ ] **Step 5: 提交合并**

```bash
git add -A
git commit -m "merge: Module A — SCNU 知识库爬虫 + 本地开发环境配置 (PR #6)"
```

Expected: 提交成功

---

### Task 3: 修复 Docker 对 scrapers 目录的包含

**Files:**
- Modify: `backend/requirements.txt`（补全爬虫依赖）
- Modify: `docker/Dockerfile.backend`（复制 scrapers/）
- Modify: `docker-compose.yml`（挂载 scrapers/）

**背景:** Dockerfile.backend 当前只 `COPY backend/ /app/`，不包含 `scrapers/` 目录。Module A 的爬虫代码在 `scrapers/`，且依赖 pdfplumber/beautifulsoup4 不在 backend requirements 中。

- [ ] **Step 1: 在 backend/requirements.txt 补全爬虫依赖**

在 `backend/requirements.txt` 末尾追加：

```
# Module A: scraper dependencies
pdfplumber>=0.10.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
```

- [ ] **Step 2: 修改 Dockerfile.backend 复制 scrapers 目录**

在 `docker/Dockerfile.backend` 的 `COPY backend/ /app/` 行之后添加：

```dockerfile
COPY scrapers/ /app/scrapers/
```

- [ ] **Step 3: 修改 docker-compose.yml 挂载 scrapers 目录**

在 backend 服务的 volumes 中添加：

```yaml
      - ./scrapers:/app/scrapers:ro
```

- [ ] **Step 4: 验证修改后的文件语法**

```bash
python -m py_compile backend/config.py
docker compose config --quiet
```

Expected: 无错误输出

- [ ] **Step 5: 提交**

```bash
git add backend/requirements.txt docker/Dockerfile.backend docker-compose.yml
git commit -m "fix: Docker 包含 scrapers 目录 + 补全爬虫依赖"
```

---

## Phase 2: 预检与合并 Module B

### Task 4: Module B 语法预检

**Files:**
- Read: `backend/services/cend_profile_analyzer.py`（在 origin/feat/module-b-ai-consulting-system 分支）
- Read: `backend/services/profile_bridge.py`（同上）
- Read: `backend/api/routes/miniapp.py`（同上，修改文件）
- Read: `backend/analytics/topic_cloud.py`（同上，修改文件）

- [ ] **Step 1: 语法预检所有 Module B 改动的 Python 文件**

```bash
$files = @(
    "backend/services/cend_profile_analyzer.py",
    "backend/services/profile_bridge.py",
    "backend/api/routes/miniapp.py",
    "backend/analytics/topic_cloud.py",
    "backend/agents/conversation/prompts_b2b.py",
    "backend/tests/benchmarks/run_accuracy.py"
)
foreach ($f in $files) {
    git show "origin/feat/module-b-ai-consulting-system:$f" | Out-File -Encoding utf8 "/tmp/$(Split-Path $f -Leaf)"
    python -m py_compile "/tmp/$(Split-Path $f -Leaf)"
}
```

Expected: 所有文件 py_compile 成功，exit code 0

- [ ] **Step 2: 检查 JSON 数据集格式有效性**

```bash
git show origin/feat/module-b-ai-consulting-system:backend/tests/benchmarks/knowledge_qa.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'KB QA: {len(d)} items')"
git show origin/feat/module-b-ai-consulting-system:backend/tests/benchmarks/profile_extraction.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'Profile: {len(d)} items')"
```

Expected: `KB QA: 100 items` 和 `Profile: 50 items`

---

### Task 5: 合并 Module B 到 main

**Files:**
- Modify: `backend/services/cend_profile_analyzer.py`（新增）
- Modify: `backend/services/profile_bridge.py`（新增）
- Modify: `backend/api/routes/miniapp.py`（修改，可能冲突）
- Modify: `backend/analytics/topic_cloud.py`（修改，可能冲突）
- Modify: `backend/agents/conversation/prompts_b2b.py`（修改）
- Modify: `.github/workflows/backend-ci.yml`（修改）
- Modify: `.gitignore`（修改）
- 新增: `backend/tests/benchmarks/*`（保留）
- 新增: `.specs/` 和 `.plans/`（保留）

- [ ] **Step 1: 记录合并前 commit hash**

```bash
git rev-parse HEAD
```

Expected: 记录此值作为 `PRE_MERGE_B_COMMIT`，用于回滚

- [ ] **Step 2: 合并 Module B 分支**

```bash
git merge origin/feat/module-b-ai-consulting-system --no-edit
```

Expected: 若无冲突，直接成功；若有冲突（miniapp.py/topic_cloud.py），进入 Step 3

- [ ] **Step 3: 解决冲突（如有）**

若 miniapp.py 或 topic_cloud.py 出现冲突：
1. 打开冲突文件，查看 `<<<<<<< HEAD` 和 `>>>>>>>` 标记
2. 保留 main 的现有逻辑 + 保留 Module B 的新增逻辑（profile_bridge 集成 + concerns 数据源）
3. 解决后：

```bash
git add backend/api/routes/miniapp.py backend/analytics/topic_cloud.py
git commit --no-edit
```

Expected: 冲突解决完成，合并提交成功

- [ ] **Step 4: 合并后全量语法预检**

```bash
python -m py_compile backend/services/cend_profile_analyzer.py backend/services/profile_bridge.py backend/api/routes/miniapp.py backend/analytics/topic_cloud.py backend/agents/conversation/prompts_b2b.py
```

Expected: 无输出，exit code 0

- [ ] **Step 5: 验证 import 链完整**

```bash
python -c "from services.cend_profile_analyzer import analyze_cend_turn, CendExtractionResult; print('cend_profile_analyzer OK')"
python -c "from services.profile_bridge import should_extract, bridge_profile_to_session_profiles; print('profile_bridge OK')"
```

Expected: 两个 import 均成功（在 backend 目录下执行）

- [ ] **Step 6: 提交合并**

```bash
git add -A
git commit -m "merge: Module B — AI 咨询系统 (cend_profile_analyzer + profile_bridge + 准确率基准)"
```

---

### Task 6: 删除分支原有测试代码

**Files:**
- Delete: `backend/tests/unit/test_cend_profile_analyzer.py`
- Delete: `backend/tests/unit/test_profile_bridge.py`
- Delete: `backend/tests/integration/test_cend_data_pipeline.py`

**说明:** 保留 benchmarks 数据集和脚本，仅删除 test_*.py（将由子代理重写）

- [ ] **Step 1: 删除分支原有测试文件**

```bash
git rm backend/tests/unit/test_cend_profile_analyzer.py
git rm backend/tests/unit/test_profile_bridge.py
git rm backend/tests/integration/test_cend_data_pipeline.py
```

Expected: 三个文件删除成功

- [ ] **Step 2: 确认 benchmarks 数据集保留**

```bash
git status backend/tests/benchmarks/
```

Expected: knowledge_qa.json、profile_extraction.json、run_accuracy.py 仍存在

- [ ] **Step 3: 提交**

```bash
git commit -m "chore: 删除分支原有测试代码，准备由独立子代理重写"
```

---

## Phase 3a: 编写测试契约文档

### Task 7: 编写 SCNU 爬虫测试契约

**Files:**
- Create: `docs/contracts/scnu_scraper_contract.md`

**原则:** 基于需求规格（PR #6 描述）编写，不读实现代码

- [ ] **Step 1: 编写契约文档**

创建 `docs/contracts/scnu_scraper_contract.md`，内容：

```markdown
# 测试契约：SCNU 知识库爬虫

## 公开接口（仅签名）

```python
class SCNUZsbAdmissionsScraper(BaseScraper):
    def fetch_admission_data(self, year: int, province: str) -> list[dict]: ...
    def parse_pdf(self, pdf_url: str) -> list[dict]: ...
```

## 行为契约

### fetch_admission_data
- 输入：年份（2022-2025）、省份（"广东" 或外省名）
- 输出：List[dict]，每条含 {year, province, subject_type, batch, min_score, min_rank}
- 契约 1：广东省份 → 返回广东表格式数据（物理/历史分组）
- 契约 2：外省 → 返回外省表格式数据（文理分组）
- 契约 3：年份不在 2022-2025 范围 → 返回空列表
- 契约 4：网络请求失败 → 重试 3 次后返回空列表（不抛异常）

### parse_pdf
- 输入：PDF 文件 URL
- 输出：List[dict]，解析 PDF 中的录取表格
- 契约 1：合法 PDF → 返回结构化表格数据
- 契约 2：PDF 无表格 → 返回空列表
- 契约 3：PDF 下载失败 → 返回空列表（不抛异常）
- 契约 4：PDF 格式异常 → 返回空列表（不抛异常）

## 边界条件
- 空省份字符串、无效年份（负数/未来年份）、不存在的省份
- PDF 文件损坏、PDF 为图片格式（无可提取文本）
- 网络超时、HTTP 404/500
```

- [ ] **Step 2: 提交**

```bash
git add docs/contracts/scnu_scraper_contract.md
git commit -m "docs: SCNU 爬虫测试契约"
```

---

### Task 8: 编写 cend_profile_analyzer 测试契约

**Files:**
- Create: `docs/contracts/cend_profile_analyzer_contract.md`

**原则:** 基于执行计划 B1 字段体系编写，不读实现代码

- [ ] **Step 1: 编写契约文档**

创建 `docs/contracts/cend_profile_analyzer_contract.md`，内容：

```markdown
# 测试契约：C-end Profile Analyzer

## 公开接口（仅签名）

```python
class CendExtractionResult:
    basic: dict          # {province, subject_type, score}
    interests: list[str] # [preferred_subjects, strong_subjects, hobbies]
    concerns: list[str]  # 自由标签
    riasec: dict         # {R, I, A, S, E, C} 各 1-10
    values: list[str]    # 价值观排序
    region_pref: dict    # {province, city}
    extra: dict          # 其他信息

    def to_dict(self) -> dict: ...
    def has_data(self) -> bool: ...

async def analyze_cend_turn(user_text: str, history_text: str, existing_profile: dict | None) -> CendExtractionResult: ...
def build_cend_analysis_prompt(user_text: str, history_text: str, existing_summary: str) -> str: ...
def parse_cend_response(text: str) -> CendExtractionResult: ...
def merge_extraction_results(existing: dict, new: CendExtractionResult) -> dict: ...
def _compute_completeness(result: CendExtractionResult) -> str: ...  # "L1" | "L2" | "L3"
```

## 行为契约

### analyze_cend_turn
- 输入：用户消息文本 + 对话历史 + 已有画像（可空）
- 输出：CendExtractionResult，含 7 字段
- 契约 1：LLM 返回合法 JSON → 返回结构化结果
- 契约 2：LLM 返回非法 JSON → 返回空结果（has_data() == False，不抛异常）
- 契约 3：LLM 超时/失败 → 返回空结果（不抛异常）
- 契约 4：existing_profile 非空 → 新提取应与已有信息合并

### build_cend_analysis_prompt
- 输入：用户消息 + 历史 + 已有画像摘要
- 输出：完整 prompt 字符串
- 契约 1：prompt 包含 7 字段定义说明
- 契约 2：prompt 包含 JSON 输出格式要求
- 契约 3：existing_summary 非空时，prompt 包含已有画像上下文

### parse_cend_response
- 输入：LLM 响应文本
- 输出：CendExtractionResult
- 契约 1：合法 JSON → 正确解析为 7 字段
- 契约 2：非法 JSON → 返回空结果（不抛异常）
- 契约 3：JSON 缺少字段 → 缺失字段为默认空值
- 契约 4：JSON 含额外字段 → 忽略额外字段

### merge_extraction_results
- 输入：已有画像 dict + 新提取 CendExtractionResult
- 输出：合并后的 dict
- 契约 1：list 字段合并去重，保留顺序（existing 优先）
- 契约 2：dict 字段深度合并，new 覆盖 existing 同名键
- 契约 3：scalar 字段，new 非空时覆盖 existing
- 契约 4：existing 为空 → 直接返回 new

### _compute_completeness
- 输入：CendExtractionResult
- 输出："L1" | "L2" | "L3"
- 契约 1：仅 basic 字段有值 → "L1"
- 契约 2：basic + interests + concerns 有值 → "L2"
- 契约 3：basic + interests + concerns + riasec + values 有值 → "L3"
- 契约 4：所有字段空 → "L1"（最低级别）

## 边界条件
- 空字符串输入、超长输入（>10000 字符）、纯标点、多语言混合
- existing_profile 为 None / 空字典 / 部分填充
- RIASEC 值超出 1-10 范围
```

- [ ] **Step 2: 提交**

```bash
git add docs/contracts/cend_profile_analyzer_contract.md
git commit -m "docs: cend_profile_analyzer 测试契约"
```

---

### Task 9: 编写 profile_bridge 测试契约

**Files:**
- Create: `docs/contracts/profile_bridge_contract.md`

- [ ] **Step 1: 编写契约文档**

创建 `docs/contracts/profile_bridge_contract.md`，内容：

```markdown
# 测试契约：Profile Bridge

## 公开接口（仅签名）

```python
async def should_extract(session_id: str) -> bool: ...
async def bridge_profile_to_session_profiles(session, tenant_id: str, user_content: str, full_content: str) -> bool: ...
async def load_existing_profile_json(session_id: str, tenant_id: str) -> dict | None: ...
async def get_chat_message_count(session_id: str) -> int: ...
```

## 行为契约

### should_extract
- 输入：session_id
- 输出：bool
- 契约 1：消息数 < 3 → 返回 False
- 契约 2：消息数 == 3 → 返回 True
- 契约 3：消息数 == 6 → 返回 True（每 3 轮触发）
- 契约 4：消息数 == 4 → 返回 False（非 3 的倍数）

### bridge_profile_to_session_profiles
- 输入：session 对象 + tenant_id + 用户消息 + 完整对话内容
- 输出：bool（是否成功更新）
- 契约 1：首次调用 → 创建 session_profiles 记录
- 契约 2：后续调用 → 更新已有记录（merge 模式）
- 契约 3：LLM 提取失败 → 返回 False（不抛异常，不写 DB）
- 契约 4：成功 → 写入 DB + 写入 JSON 备份文件
- 契约 5：DB 写入成功但 JSON 备份失败 → 仍返回 True（JSON 备份非关键路径）

### load_existing_profile_json
- 输入：session_id + tenant_id
- 输出：dict | None
- 契约 1：记录存在 → 返回 profile_json
- 契约 2：记录不存在 → 返回 None

### get_chat_message_count
- 输入：session_id
- 输出：int
- 契约 1：无消息 → 返回 0
- 契约 2：N 条消息 → 返回 N

## 边界条件
- session_id 不存在
- tenant_id 不匹配（租户隔离）
- 并发调用同一 session_id
- DB 连接失败
```

- [ ] **Step 2: 提交**

```bash
git add docs/contracts/profile_bridge_contract.md
git commit -m "docs: profile_bridge 测试契约"
```

---

### Task 10: 编写 miniapp SSE 测试契约

**Files:**
- Create: `docs/contracts/miniapp_sse_contract.md`

- [ ] **Step 1: 编写契约文档**

创建 `docs/contracts/miniapp_sse_contract.md`，内容：

```markdown
# 测试契约：Mini-app SSE 对话端点

## 公开接口

```
POST /api/v1/miniapp/chat (SSE)
Headers: X-Tenant: <tenant_slug>
Body: {session_id, message}
Response: SSE stream
```

## 行为契约

### SSE 对话响应
- 契约 1：发送消息 → 返回 SSE 流，含 assistant_message
- 契约 2：每 3 轮对话 → 触发 profile_bridge，响应含 profile_updated: true
- 契约 3：非 3 倍数轮次 → profile_updated: false
- 契约 4：profile_bridge 失败 → 不阻塞 SSE 响应，仅日志 warning
- 契约 5：缺少 X-Tenant 头 → 400 错误

### profile_updated 字段
- 契约 1：bridge 成功 → profile_updated: true
- 契约 2：bridge 未触发 → profile_updated: false
- 契约 3：bridge 失败 → profile_updated: false（不抛异常）

## 边界条件
- 空 message、超长 message
- 无效 session_id
- 租户隔离：A 租户 session 不被 B 租户访问
```

- [ ] **Step 2: 提交**

```bash
git add docs/contracts/miniapp_sse_contract.md
git commit -m "docs: miniapp SSE 测试契约"
```

---

### Task 11: 编写 analytics 数据消费测试契约

**Files:**
- Create: `docs/contracts/analytics_consumption_contract.md`

- [ ] **Step 1: 编写契约文档**

创建 `docs/contracts/analytics_consumption_contract.md`，内容：

```markdown
# 测试契约：分析看板数据消费

## 公开接口

```
GET /api/v1/analytics/topic-cloud
GET /api/v1/analytics/profile-dashboard
GET /api/v1/analytics/region-distribution
```

## 行为契约

### topic_cloud
- 契约 1：session_profiles.concerns 有数据 → concerns 词频权重 x2
- 契约 2：concerns 为空 → 仅返回普通词频
- 契约 3：返回 Top 50 词汇
- 契约 4：租户隔离，只返回当前租户数据

### profile_dashboard
- 契约 1：session_profiles 有数据 → 返回 RIASEC 雷达 + 价值观分布 + 完整度分布
- 契约 2：无数据 → 返回空结构（不报错）
- 契约 3：租户隔离

### region_distribution
- 契约 1：session_profiles.profile_json.region_pref 有数据 → 返回地域分布
- 契约 2：无数据 → 返回空结构
- 契约 3：租户隔离

## 边界条件
- session_profiles 表为空
- profile_json 字段缺失
- concerns 为非 list 类型
```

- [ ] **Step 2: 提交**

```bash
git add docs/contracts/analytics_consumption_contract.md
git commit -m "docs: analytics 数据消费测试契约"
```

---

## Phase 3b: 生成模块索引文档

### Task 12: 生成 MODULE_INDEX.md

**Files:**
- Create: `docs/MODULE_INDEX.md`

**说明:** 此文档仅包含公开接口签名和功能概述，供子代理阅读。不含实现细节。

- [ ] **Step 1: 编写模块索引文档**

创建 `docs/MODULE_INDEX.md`，内容：

```markdown
# 模块代码索引 — Module A + Module B

## Module A: 知识库搭建（PR #6）

### scrapers/sources/scnu_zsb_admissions.py
- 功能：从 zsb.scnu.edu.cn 抓取 2022-2025 年录取数据 PDF 并解析
- 类：SCNUZsbAdmissionsScraper(BaseScraper)
- 输入：HTML 页面 URL（广东/外省双表）
- 输出：List[dict]（年份/省份/科类/批次/最低分/最低位次）
- 依赖：pdfplumber, BeautifulSoup, base_scraper.BaseScraper

### docker-compose.yml（修改）
- 改动：暴露 db(5432) 和 redis(6379) 端口到宿主机

### scrapers/base_scraper.py（修改）
- 改动：tenacity 9.0 兼容性修复

### backend/config.py（修改）
- 改动：CORS 端口支持扩展

---

## Module B: AI 咨询体系

### backend/services/cend_profile_analyzer.py（+486 行）
- 功能：独立 LLM 提取器，从单轮对话提取结构化学生画像
- 类：CendExtractionResult（7 字段：basic/interests/concerns/riasec/values/region_pref/extra）
- 函数：
  - async analyze_cend_turn(user_text, history_text, existing_profile) -> CendExtractionResult
  - build_cend_analysis_prompt(user_text, history_text, existing_summary) -> str
  - parse_cend_response(text: str) -> CendExtractionResult
  - merge_extraction_results(existing: dict, new: CendExtractionResult) -> dict
  - _compute_completeness(result: CendExtractionResult) -> str  # "L1"|"L2"|"L3"
- 输入：对话文本 + 已有画像（可选）
- 输出：CendExtractionResult（含 completeness 字段）
- 依赖：DeepSeek API, models.async_session

### backend/services/profile_bridge.py（+321 行）
- 功能：将 C-end LLM 提取结果桥接到 session_profiles 表 + JSON 备份
- 函数：
  - async should_extract(session_id: str) -> bool
  - async bridge_profile_to_session_profiles(session, tenant_id, user_content, full_content) -> bool
  - async load_existing_profile_json(session_id: str, tenant_id: str) -> Optional[dict]
  - async get_chat_message_count(session_id: str) -> int
- 输入：session_id, tenant_id, user_content, full_content
- 输出：bool（是否成功更新）+ 副作用（写 DB + 写 JSON 文件）
- 依赖：cend_profile_analyzer, tenants.models.SessionProfile

### backend/api/routes/miniapp.py（修改，+14 行）
- 改动：SSE 响应完成后调用 profile_bridge
- 集成点：每 3 轮对话触发 bridge_profile_to_session_profiles()
- 容错：bridge 失败不阻塞 SSE 响应，仅 warning 日志

### backend/analytics/topic_cloud.py（修改，+13 行）
- 改动：新增 session_profiles.profile_json.concerns 数据源
- 权重：concerns 词频 x2（高于普通词频 x1）

### backend/agents/conversation/prompts_b2b.py（修改，+4 行）
- 改动：B2B prompt 微调

### 测试与基准（保留）
- tests/benchmarks/knowledge_qa.json — 100 对 KB Q&A ground truth
- tests/benchmarks/profile_extraction.json — 50 对提取 ground truth
- tests/benchmarks/run_accuracy.py — 准确率评测脚本

### CI 与配置
- .github/workflows/backend-ci.yml — 添加 95% 阈值准确率基准步骤
- .gitignore — data/extracted_profiles/ 加入忽略
```

- [ ] **Step 2: 提交**

```bash
git add docs/MODULE_INDEX.md
git commit -m "docs: 模块代码索引文档（公开接口签名）"
```

---

## Phase 4: 并行派发子代理重写测试

### Task 13: 派发子代理 A — 单元测试

**说明:** 此任务由独立子代理执行。子代理在独立上下文中工作，只读契约文档 + 接口签名，不读实现代码。

**子代理输入:**
- `docs/contracts/scnu_scraper_contract.md`
- `docs/contracts/cend_profile_analyzer_contract.md`
- `docs/contracts/profile_bridge_contract.md`
- `docs/contracts/analytics_consumption_contract.md`
- `docs/MODULE_INDEX.md`
- `backend/tests/conftest.py`（了解 fixture）

**子代理禁止:**
- 读取 `backend/services/cend_profile_analyzer.py` 函数体
- 读取 `backend/services/profile_bridge.py` 函数体
- 读取 `backend/analytics/topic_cloud.py` 函数体
- 读取 `scrapers/sources/scnu_zsb_admissions.py` 函数体
- 读取任何分支原有测试代码

**子代理输出:**
- `backend/tests/unit/test_scnu_scraper.py`
- `backend/tests/unit/test_cend_profile_analyzer.py`
- `backend/tests/unit/test_profile_bridge.py`
- `backend/tests/unit/test_topic_cloud.py`

- [ ] **Step 1: 派发子代理 A**

使用 subagent-driven-development 技能派发独立子代理，提供上述输入文件路径和禁止项清单。子代理任务：

"阅读 docs/contracts/ 下的 4 份测试契约文档和 docs/MODULE_INDEX.md。根据契约编写单元测试，覆盖所有行为契约和边界条件。遵循 AAA 模式（Arrange/Act/Assert 注释分隔）。使用 conftest.py 中的 fixture（test_tenant、seed_session_profile 等）。LLM 调用必须 mock。禁止读取实现代码。"

- [ ] **Step 2: 子代理 A 编写 4 个测试文件**

子代理产出：
- `test_scnu_scraper.py` — 覆盖 fetch_admission_data、parse_pdf 全部契约
- `test_cend_profile_analyzer.py` — 覆盖 analyze_cend_turn、parse_cend_response、merge_extraction_results、_compute_completeness 全部契约
- `test_profile_bridge.py` — 覆盖 should_extract、bridge_profile_to_session_profiles、load_existing_profile_json、get_chat_message_count 全部契约
- `test_topic_cloud.py` — 覆盖 concerns 数据源、权重计算、Top50 截断

- [ ] **Step 3: 运行单元测试验证**

```bash
cd backend
python -m pytest tests/unit/test_scnu_scraper.py tests/unit/test_cend_profile_analyzer.py tests/unit/test_profile_bridge.py tests/unit/test_topic_cloud.py -v
```

Expected: 所有测试通过（若有失败，子代理修复测试，不修改实现代码）

- [ ] **Step 4: 提交**

```bash
git add backend/tests/unit/test_scnu_scraper.py backend/tests/unit/test_cend_profile_analyzer.py backend/tests/unit/test_profile_bridge.py backend/tests/unit/test_topic_cloud.py
git commit -m "test: 单元测试重写（契约驱动，子代理 A）"
```

---

### Task 14: 派发子代理 B — 集成测试

**说明:** 独立子代理执行，同 Task 13 的隔离规则。

**子代理输入:**
- `docs/contracts/scnu_scraper_contract.md`
- `docs/contracts/cend_profile_analyzer_contract.md`
- `docs/contracts/profile_bridge_contract.md`
- `docs/contracts/miniapp_sse_contract.md`
- `docs/contracts/analytics_consumption_contract.md`
- `docs/MODULE_INDEX.md`
- `backend/tests/conftest.py`

**子代理输出:**
- `backend/tests/integration/test_scraper_pipeline.py`
- `backend/tests/integration/test_cend_data_pipeline.py`
- `backend/tests/integration/test_analytics_consumption.py`

- [ ] **Step 1: 派发子代理 B**

子代理任务：

"阅读 docs/contracts/ 下的 5 份测试契约文档和 docs/MODULE_INDEX.md。根据契约编写集成测试，覆盖完整链路：爬虫→知识库索引、SSE对话→画像提取→session_profiles写入、分析看板数据消费。使用 async_client fixture 进行 API 测试。LLM 调用必须 mock。禁止读取实现代码。"

- [ ] **Step 2: 子代理 B 编写 3 个测试文件**

子代理产出：
- `test_scraper_pipeline.py` — 爬虫数据 → ChromaDB 写入 → 检索 API 验证
- `test_cend_data_pipeline.py` — SSE 发消息 → 3 轮触发 bridge → session_profiles 写入 → JSON 备份 → profile_updated 字段
- `test_analytics_consumption.py` — topic_cloud 读 concerns → profile_dashboard 读 RIASEC → region_distribution 读地域 → 租户隔离

- [ ] **Step 3: 运行集成测试验证**

```bash
cd backend
python -m pytest tests/integration/test_scraper_pipeline.py tests/integration/test_cend_data_pipeline.py tests/integration/test_analytics_consumption.py -v
```

Expected: 所有测试通过

- [ ] **Step 4: 提交**

```bash
git add backend/tests/integration/test_scraper_pipeline.py backend/tests/integration/test_cend_data_pipeline.py backend/tests/integration/test_analytics_consumption.py
git commit -m "test: 集成测试重写（契约驱动，子代理 B）"
```

---

### Task 15: 派发子代理 C — 端到端测试

**说明:** 独立子代理执行。E2E 测试基于 Docker 全栈，使用 Playwright。

**子代理输入:**
- `docs/contracts/miniapp_sse_contract.md`
- `docs/contracts/analytics_consumption_contract.md`
- `docs/MODULE_INDEX.md`
- `backend/tests/e2e/conftest.py`（了解 E2E fixture 模式）
- `backend/tests/e2e/test_student_journey.py`（了解现有 E2E 模式，仅参考结构不参考断言）

**子代理输出:**
- `backend/tests/e2e/test_student_journey.py`（重写）
- `backend/tests/e2e/test_admin_dashboard.py`（重写）

- [ ] **Step 1: 派发子代理 C**

子代理任务：

"阅读 docs/contracts/ 下的 miniapp_sse 和 analytics_consumption 契约文档。编写端到端测试，使用 Playwright（sync_playwright，headless Chromium，BASE_URL='http://nginx'）。覆盖：学生端对话 6 轮 → session_profiles 有记录 → 管理后台画像看板显示数据。参考 backend/tests/e2e/conftest.py 的 fixture 模式。禁止读取实现代码。"

- [ ] **Step 2: 子代理 C 编写 2 个 E2E 测试文件**

子代理产出：
- `test_student_journey.py` — 小程序对话 6 轮 → 验证 profile_bridge 触发 → 验证 session_profiles 有记录
- `test_admin_dashboard.py` — 管理员登录 → 画像看板 → 验证 RIASEC/地域/词云有数据（非 mock）

- [ ] **Step 3: 运行 E2E 测试验证（需 Docker 全栈运行）**

```bash
cd backend
python -m pytest tests/e2e/test_student_journey.py tests/e2e/test_admin_dashboard.py -v
```

Expected: 所有 E2E 测试通过（需先完成 Phase 5 的 Docker 启动）

- [ ] **Step 4: 提交**

```bash
git add backend/tests/e2e/test_student_journey.py backend/tests/e2e/test_admin_dashboard.py
git commit -m "test: E2E 测试重写（契约驱动，子代理 C）"
```

---

## Phase 5: Docker 全栈验证

### Task 16: Docker 全栈启动

- [ ] **Step 1: 构建并启动所有服务**

```bash
docker compose up -d --build
```

Expected: 6 服务（db/redis/backend/admin-spa/mini-app/nginx）全部启动

- [ ] **Step 2: 等待服务健康**

```bash
docker compose ps
```

Expected: 所有服务 STATUS 为 healthy 或 running

- [ ] **Step 3: 验证后端启动日志**

```bash
docker compose logs backend | Select-String "init_db|ensure_tenant|auto_import|embedding|Application startup"
```

Expected: 看到 init_db → ensure_tenant → auto_import_knowledge → embedding 预热 → startup complete

- [ ] **Step 4: 验证 nginx 路由可达**

```bash
curl -s http://localhost/api/health
```

Expected: 返回 `{"status":"ok"}` 或类似健康响应

---

### Task 17: 运行全部测试

- [ ] **Step 1: 在 backend 容器内运行单元测试**

```bash
docker compose exec backend python -m pytest tests/unit/ -v --tb=short
```

Expected: 全部通过

- [ ] **Step 2: 运行集成测试**

```bash
docker compose exec backend python -m pytest tests/integration/ -v --tb=short
```

Expected: 全部通过

- [ ] **Step 3: 运行 E2E 测试**

```bash
docker compose exec backend python -m pytest tests/e2e/ -v --tb=short
```

Expected: 全部通过

- [ ] **Step 4: 运行准确率基准测试**

```bash
docker compose exec backend python tests/benchmarks/run_accuracy.py
```

Expected: KB Q&A 准确率 ≥95%、提取准确率 ≥95%（低于 95% 为 warning，不阻塞）

- [ ] **Step 5: 汇总测试结果**

记录各层测试通过率和基准准确率。若有失败，进入错误处理流程（见设计文档第 8 节）。

---

## Phase 6: 提供本地体验链接

### Task 18: 验证体验链接并输出

- [ ] **Step 1: 验证小程序入口**

```bash
curl -s -o NUL -w "%{http_code}" http://localhost/
```

Expected: 200

- [ ] **Step 2: 验证管理后台入口**

```bash
curl -s -o NUL -w "%{http_code}" http://localhost/admin/
```

Expected: 200

- [ ] **Step 3: 验证 API 文档入口**

```bash
curl -s -o NUL -w "%{http_code}" http://localhost/api/docs
```

Expected: 200

- [ ] **Step 4: 输出体验链接和脚本**

向用户输出：

```
✅ 全部测试通过，Docker 全栈运行中。

本地体验链接：
  - 学生端小程序：http://localhost/
  - 管理后台：http://localhost/admin/
  - API 文档：http://localhost/api/docs
  - 后端日志：docker compose logs -f backend

人工体验脚本：
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

## 验证标准汇总

| 检查项 | 方法 | 标准 |
|--------|------|------|
| 语法预检 | py_compile | 0 errors |
| 单元测试 | pytest tests/unit/ -v | 100% pass |
| 集成测试 | pytest tests/integration/ -v | 100% pass |
| E2E 测试 | pytest tests/e2e/ -v | 100% pass |
| 准确率（KB） | run_accuracy.py | ≥95%（warning） |
| 准确率（提取） | run_accuracy.py | ≥95%（warning） |
| Docker 全栈 | docker compose up -d | 6 服务健康 |
| 本地体验 | 浏览器访问 3 个链接 | 功能正常 |
