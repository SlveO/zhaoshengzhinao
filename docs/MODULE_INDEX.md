# 模块代码索引 — Module A + Module B

> 此文档仅包含公开接口签名和功能概述，供测试子代理阅读。不含实现细节。

## Module A: 知识库搭建（PR #6）

### scrapers/sources/scnu_zsb_admissions.py
- **功能**：从 zsb.scnu.edu.cn 抓取 2022-2025 年录取数据 PDF 并解析
- **类**：`SCNUZsbAdmissionsScraper(BaseScraper)`
- **公开方法**：
  - `async run() -> dict` — 返回 {source, records, errors, output}
- **内部方法**（测试可通过子类覆盖）：
  - `async _get_year_map(client) -> dict` — 获取年份→文章URL映射
  - `async _find_pdf_url(client, article_url) -> str|None` — 从文章页找PDF链接
  - `_parse_pdf_table(pdf_bytes, year, province_type) -> list[dict]` — 解析PDF表格
- **模块级函数**：`_extract_pdf_urls(html_text) -> list[str]`
- **输入**：无（构造时确定配置）
- **输出**：list[dict]（年份/省份/科类/批次/最低分/最低位次）
- **依赖**：pdfplumber, BeautifulSoup, httpx, BaseScraper

### scrapers/base_scraper.py（修改）
- **改动**：tenacity 9.0 兼容性修复

### backend/config.py（修改）
- **改动**：CORS 端口支持扩展

### docker-compose.yml（修改）
- **改动**：暴露 db(5432) 和 redis(6379) 端口到宿主机

---

## Module B: AI 咨询体系

### backend/services/cend_profile_analyzer.py（+486 行）
- **功能**：独立 LLM 提取器，从单轮对话提取结构化学生画像
- **数据类**：`CendExtractionResult`（8 字段）
  - `basic: dict` — {province, subject_type, score}
  - `interests: dict` — {preferred_subjects: list, strong_subjects: list, hobbies: list}
  - `concerns: list` — 自由标签
  - `riasec: dict` — {R,I,A,S,E,C} 各 0-10
  - `values: list` — 价值观排序
  - `region_pref: dict` — {province, city}
  - `extra: dict` — 其他信息
  - `completeness: str` — "L1"|"L2"|"L3"
- **方法**：
  - `to_profile_json() -> dict` — 导出为可序列化 dict
  - `has_any_data() -> bool` — 是否有有意义数据
- **函数**：
  - `async analyze_cend_turn(user_msg, ai_reply, existing_profile=None, _conversation_history=None, max_retries=2) -> CendExtractionResult`
  - `build_cend_analysis_prompt(user_msg, ai_reply, existing_profile) -> str`
  - `parse_cend_response(text: str) -> CendExtractionResult`
  - `merge_extraction_results(existing: CendExtractionResult, new_extraction: CendExtractionResult) -> CendExtractionResult`
  - `_compute_completeness(result: CendExtractionResult) -> str`
  - `_summarize_existing(existing_profile: Optional[dict]) -> str`
  - `_dedup_merge_lists(existing_list: list, new_list: list) -> list`
- **输入**：对话文本（user_msg + ai_reply）+ 已有画像（可选）
- **输出**：CendExtractionResult（含 completeness 字段）
- **依赖**：DeepSeek API (langchain_openai.ChatOpenAI), config.settings

### backend/services/profile_bridge.py（+321 行）
- **功能**：将 C-end LLM 提取结果桥接到 session_profiles 表 + JSON 备份
- **函数**：
  - `async get_chat_message_count(session_id: str) -> int`
  - `async should_extract(session_id: str) -> bool` — count > 0 AND count % 3 == 0
  - `async load_existing_profile_json(tenant_id: uuid.UUID, session_id: uuid.UUID) -> Optional[dict]`
  - `async bridge_profile_to_session_profiles(session: ConsultSession, tenant_id: uuid.UUID, user_content: str, assistant_content: str) -> bool`
  - `_compute_confidence(result: CendExtractionResult) -> dict`
  - `_ensure_backup_dir() -> None`
  - `_dict_to_extraction_result(data: Optional[dict]) -> CendExtractionResult`
- **输入**：session, tenant_id, user_content, assistant_content
- **输出**：bool（是否成功更新）+ 副作用（写 DB + 写 JSON 文件）
- **关键特性**：NEVER raise — 所有异常被 catch，失败返回 False
- **依赖**：cend_profile_analyzer, models.async_session, tenants.models.SessionProfile, core.event_writer

### backend/api/routes/miniapp.py（修改，+14 行）
- **改动**：SSE 响应完成后调用 profile_bridge
- **集成点**：
  - 调用时机：assistant 消息保存后，regex 提取前
  - 调用条件：`tenant_id 非空 AND should_extract(session_id) == True`
  - 调用：`bridge_profile_to_session_profiles(session, tenant_id, user_content, full_content)`
  - 容错：try/except 包裹，异常时 logging.warning，不阻塞 SSE
- **响应字段**：`profile_updated = profile_updated_regex OR profile_bridge_ran`

### backend/analytics/topic_cloud.py（修改，+13 行）
- **改动**：新增 session_profiles.profile_json.concerns 数据源
- **SQL**：`SELECT jsonb_array_elements_text(profile_json->'concerns') FROM session_profiles WHERE ...`
- **权重**：concerns 词频 x2（高于普通词频 x1）

### backend/agents/conversation/prompts_b2b.py（修改，+4 行）
- **改动**：B2B prompt 微调

### 测试与基准（保留）
- `tests/benchmarks/knowledge_qa.json` — 100 对 KB Q&A ground truth
- `tests/benchmarks/profile_extraction.json` — 50 对提取 ground truth
- `tests/benchmarks/run_accuracy.py` — 准确率评测脚本（KB ≥95%, 提取 ≥95%）

### CI 与配置
- `.github/workflows/backend-ci.yml` — 添加 95% 阈值准确率基准步骤
- `.gitignore` — data/extracted_profiles/ 加入忽略

---

## 测试基础设施

### backend/tests/conftest.py
- **fixture**：`event_loop`, `setup_db`, `test_tenant`, `seed_event`, `seed_session_profile`, `async_client`
- **环境**：`DATABASE_URL=postgresql+asyncpg://gaokao:gaokao@db:5432/gaokao_test`

### backend/tests/e2e/conftest.py
- **fixture**：`setup_db`（覆盖父级，E2E 不需要 per-test DB cleanup）
- **模式**：`sync_playwright`, `BASE_URL="http://nginx"`, headless Chromium
