# 推荐模块代码文件全览

> 最后更新: 2026-05-15 | 分支: main | 共 22 个文件，6 层

## 一、API 路由层

### `backend/api/routes/recommendation.py`
**负责模块：** 推荐 API 路由  
**包含：** 3 个 HTTP 端点 + Redis 缓存逻辑  
**实现效果：**

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/recommendations` | GET | 返回推荐列表（Redis TTL 600s 缓存） |
| `/api/v1/recommendations/feedback` | POST | 提交反馈（useful/not_relevant） |
| `/api/v1/recommendations/{rec_id}` | GET | 按 ID 获取单条推荐详情 |

**关键函数：**
- `get_recommendations()` — 检查缓存 → 加载画像 → 调用生成服务 → 缓存结果
- `submit_feedback()` — 创建 `RecommendationFeedback` 记录
- `_get_cached_recommendations()` / `_cache_recommendations()` — Redis 读写辅助

---

## 二、业务服务层

### `backend/services/recommendation_service.py`
**负责模块：** 推荐核心编排引擎  
**实现效果：** 检索候选 → 行业数据丰富化 → 用户反馈注入 → LLM 排序 → 结果持久化

**关键常量/函数：**

| 组件 | 功能 |
|------|------|
| `RANKING_PROMPT` | 主排序提示词，要求输出冲/稳/保三级 + 数据来源 |
| `L1_PROMPT_ADDON` | 基础推荐策略：100% 位次匹配 |
| `L2_PROMPT_ADDON` | 较完整推荐：60% 位次 + 25% 兴趣 + 15% 地域 |
| `L3_PROMPT_ADDON` | 深度推荐：40% 位次 + 35% 兴趣 + 15% 价值观 + 10% 地域 |
| `_get_adaptive_prompt()` | 根据 `completeness` 字段选择匹配策略 |
| `generate_recommendations()` | 核心编排：retriever → 行业丰富 → 反馈注入 → LLM 排序 |
| `_call_llm_with_retry()` | tenacity 指数退避重试（2次，90s 超时） |

**LLM 配置：** `deepseek-chat`，temperature=0.3，max_tokens=4096，timeout=120s

---

## 三、知识库 / RAG 层

### `backend/knowledge_base/chroma_client.py`
**负责模块：** ChromaDB 向量数据库封装  
**实现效果：** 管理 `colleges_majors` 集合，提供文档索引写入与语义搜索

| 组件 | 功能 |
|------|------|
| `collection` | Chroma 集合对象（194,041 文档） |
| `_sanitize_meta()` | 过滤 metadata 中的 None 值（Chroma 0.5.x 不允许） |
| `index_documents()` | 批量嵌入文档并写入集合 |
| `search_similar()` | 语义向量查询，返回文档+元数据+余弦距离 |

---

### `backend/knowledge_base/retriever.py`
**负责模块：** 混合检索管道  
**实现效果：** 三步过滤管线，从 194K 文档中精准筛选候选

**检索流程：**
```
用户画像 → build_query_text(RIASEC→中文关键词)
  → Chroma 语义搜索 (k × 3, min 100)
  → 科目过滤（子串匹配，支持"首选物理，再选不限"复合格式）
  → 院校多样性控制（每校最多 3 条）
  → 候选列表
```

| 函数 | 功能 |
|------|------|
| `build_query_text()` | 将 RIASEC 维度映射为中文语义关键词 |
| `retrieve_candidates()` | 混合检索主函数（语义+规则过滤+多样性） |

---

### `backend/knowledge_base/embeddings.py`
**负责模块：** 嵌入模型管理  
**实现效果：** 加载 `BAAI/bge-large-zh-v1.5`（1024 维），ModelScope 优先下载

| 组件 | 功能 |
|------|------|
| `_get_model()` | 延迟加载 SentenceTransformer，ModelScope → HuggingFace 回退 |
| `EmbeddingWrapper` | 封装 `embed_documents()` / `embed_query()`，L2 归一化 |
| `embedding_model` | 模块级单例，所有 Chroma 操作共用 |

---

## 四、数据模型层

### `backend/models/college.py`
**表：** `colleges` | **记录：** 162 条（粤 65 + 京 63 + 沪 34）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `name` | String | 院校名称 |
| `code` | String | 教育部代码（唯一） |
| `type` | String | 类型（综合/理工/师范等） |
| `level` | String | 层次（985/211/双一流/省重点/普通本科） |
| `province` | String | 省份 |
| `city` | String | 城市 |
| `is_985` | Boolean | 是否 985 |
| `is_211` | Boolean | 是否 211 |
| `is_double_first` | Boolean | 是否双一流 |
| `intro` | Text | 院校简介 |

---

### `backend/models/admission.py`
**表：** `admission_data` | **记录：** 194,041 条（31 省 × 2020-2024）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID | 主键 |
| `college_id` | UUID | 外键 → colleges |
| `major_name` | String | 专业名称 |
| `year` | Integer | 年份 |
| `province` | String | 录取省份 |
| `batch` | String | 批次 |
| `min_score` | Integer | 最低录取分数 |
| `min_rank` | Integer | 最低录取位次 |
| `subject_requirements` | String | 选科要求（如"首选物理，再选不限"） |
| `source_url` | String | 数据来源 URL |

---

### `backend/models/industry.py`
**表：** `industry_analysis` | **记录：** 60 条（10 行业 × 6 年）

| 字段 | 说明 |
|------|------|
| `industry_name` | 行业名称 |
| `avg_annual_salary` | 年均薪资 |
| `salary_growth_rate` | 薪资增长率 |
| `employment_demand_index` | 就业需求指数（1-5） |
| `entry_difficulty` | 入行难度 |
| `outlook` | 行业前景描述 |
| `popular_positions` | 热门岗位（JSONB） |
| `pros` / `cons` | 行业优缺点（JSONB） |

---

### `backend/models/mapping.py`
**表：** `major_industry_mapping` | **记录：** 20 条

| 字段 | 说明 |
|------|------|
| `major_name` | 专业名称 |
| `primary_industries` | 主要对口行业（JSONB 列表） |
| `secondary_industries` | 次要对口行业（JSONB 列表） |
| `typical_positions` | 典型岗位（JSONB 列表） |
| `salary_range` | 薪资范围 `{entry, senior}`（JSONB） |

---

### `backend/models/recommendation.py`
**表：** `recommendations`  
**实现效果：** 持久化每次推荐结果，支持历史查询

| 字段 | 说明 |
|------|------|
| `id` | UUID 主键 |
| `user_id` | 用户 ID（已索引） |
| `profile_version` | 画像版本号 |
| `result_json` | 完整推荐列表（JSONB） |
| `created_at` | 创建时间 |

---

### `backend/models/recommendation_feedback.py`
**表：** `recommendation_feedback`  
**实现效果：** 记录用户反馈，注入后续推荐排序形成闭环

| 字段 | 说明 |
|------|------|
| `id` | UUID 主键 |
| `user_id` | 用户 ID（已索引） |
| `college_name` | 院校名称 |
| `major_name` | 专业名称 |
| `feedback_type` | `"useful"` 或 `"not_relevant"` |

---

### `backend/schemas/recommendation.py`
**负责模块：** Pydantic 响应模型  
**包含：** `RecommendationResponse` — 字段 `recommendations: list[dict]` + `profile_snapshot: dict`

---

## 五、索引脚本

| 文件 | 位置 | 功能 | 运行环境 |
|------|------|------|---------|
| `index_chroma.py` | `backend/` | 生产索引器，batch=2000 | Docker 内 |
| `index_chroma.py` | `scripts/` | 开发索引器，含行业数据丰富，batch=10000 | 宿主机 |
| `monitor_chroma.py` | `scripts/` | 实时索引进度监控（速度/ETA/DB 大小） | 宿主机 |

---

## 六、前端层

### `frontend/src/pages/Recommendations.tsx`
**负责模块：** 推荐页面  
**实现效果：** 三种状态渲染——加载中（微调器 + 计时器）、错误（重试按钮）、成功（筛选栏 + 卡片列表）

---

### `frontend/src/components/recommendation/RecommendationCard.tsx`
**负责模块：** 单条推荐卡片  
**实现效果：**

| 视觉元素 | 效果 |
|---------|------|
| 左侧彩色条 | 红=冲刺 / 绿=稳妥 / 蓝=保底 |
| 院校名+层级徽章 | 985/211/双一流标识 |
| 匹配分 | 综合评分 |
| 三进度条 | 录取概率 / 兴趣匹配 / 前景评分 |
| 可折叠理由 | 每条理由：emoji + 来源 URL + 置信度 |
| 反馈按钮 | "有用" / "不相关"，乐观 UI 更新 |

---

### `frontend/src/components/recommendation/ProfileSummaryBar.tsx`
**负责模块：** 画像摘要栏  
**实现效果：** 分数 + 兴趣类型（RIASEC → 中文标签）+ 地域偏好 + L1-L4 完整度标签 + 返回对话链接

---

### `frontend/src/components/recommendation/FilterBar.tsx`
**负责模块：** 筛选控件  
**实现效果：** 按层次（985/211/双一流/省重点）+ 城市（广州/深圳/珠海/汕头/东莞）+ 总数统计

---

### `frontend/src/stores/recommendationStore.ts`
**负责模块：** Zustand 状态管理  
**实现效果：** `recommendations` / `profileSnapshot` / `filters` / `loading` / `error` / `load()` / `setFilter()`

---

### `frontend/src/services/recommendation.ts`
**负责模块：** 前端 API 调用  
**包含：**
- `getRecommendations()` — `GET /api/v1/recommendations`
- `submitFeedback(collegeName, majorName, feedbackType)` — `POST /api/v1/recommendations/feedback`

---

### `frontend/src/types/index.ts`（推荐相关类型）
| 接口 | 字段 |
|------|------|
| `Recommendation` | `rank`, `college_name`, `major_name`, `level`, `city`, `category`, `match_score`, `reasons[]`, `scores{admission_probability, interest_match, career_prospect}` |
| `Reason` | `type`, `content`, `source`, `source_url`, `confidence` |
| `ProfileSlot` | `score`, `subjects`, `riasec`, `values`, `region_pref`, `completeness`(L1-L4), `engagement` |

---

## 完整数据流

```
┌─ 前端 ──────────────────────────────────────────────────────────┐
│  /recommendations → recStore.load() → recApi.getRecommendations()│
└──────────────────────────────┬──────────────────────────────────┘
                               │ GET /api/v1/recommendations
                               ▼
┌─ 路由层 ────────────────────────────────────────────────────────┐
│  Redis 缓存检查 → 命中? 直接返回                                 │
│  未命中 → 加载画像 → 回填 user 表数据 → 调用 generate_recommendations │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─ 服务层 ────────────────────────────────────────────────────────┐
│  1. retrieve_candidates(profile, k=30)                          │
│  2. 查询 MajorIndustryMapping + IndustryAnalysis 丰富化          │
│  3. 查询 RecommendationFeedback 调整排序                        │
│  4. _get_adaptive_prompt() 选择 L1/L2/L3 策略                   │
│  5. deepseek-chat LLM 排序 (retry×2, timeout 90s)              │
│  6. JSON 解析 → 写入 recommendations 表                         │
│  7. Redis 缓存 (TTL 600s)                                       │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─ RAG 层 ────────────────────────────────────────────────────────┐
│  画像 → build_query_text(RIASEC → 中文关键词)                    │
│  → Chroma 语义搜索 (k×3, min 100) → 194K 文档                   │
│  → 科目子串匹配过滤                                             │
│  → 院校多样性 ≤3/校                                            │
│  → 返回候选列表                                                 │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
┌─ 前端渲染 ──────────────────────────────────────────────────────┐
│  ProfileSummaryBar + FilterBar + RecommendationCard × N         │
│  用户反馈 → POST /feedback → 写入 feedback 表 → 影响下次排序      │
└─────────────────────────────────────────────────────────────────┘
```
