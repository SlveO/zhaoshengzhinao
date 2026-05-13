# 基于心理学引导的高考志愿填报系统 — 完整设计方案

## 一、项目概述与背景分析

### 1.1 项目定位
面向高考学生的智能志愿填报辅助系统，核心差异化在于**通过心理学引导对话深度挖掘学生隐性需求**，结合RAG知识库与数据分析，提供个性化、可溯源的志愿推荐。

### 1.2 README原方案评审

**优点：**
- 智能体职责划分清晰，对话引导→数据分析→推荐的三层递进合理
- 数据管道分层（收集→过滤→清洗→审核）符合ETL工程规范
- 意识到了数据安全的重要性（用户数据加密）

**需改进的问题：**

| 问题 | 说明 | 建议 |
|------|------|------|
| 缺少对话管理机制 | 心理学引导对话需要多轮状态管理、意图识别、情感分析 | 增加对话状态机 + 心理学话术库 |
| RAG方案未细化 | 仅提及"是否需要改进"，未说明检索策略 | 采用混合检索（向量+关键词）+ 重排序 |
| 数据管道缺乏闭环 | 审核后的数据如何反哺知识库未说明 | 增加数据反馈环路 |
| 缺少评测体系 | 推荐结果好坏如何衡量？ | 建立离线评测+在线A/B测试框架 |
| 用户画像无更新机制 | 画像应是动态的，随对话深入逐步完善 | 设计增量画像更新策略 |
| 缺少监控与可观测性 | 多智能体系统需要全链路追踪 | 集成LangSmith/LangFuse等追踪工具 |
| 人机协作界面未设计 | 人工审核环节需要可视化操作界面 | 设计审核工作台 |

---

## 二、系统总体架构

### 2.1 架构选型：模块化单体 + 异步任务队列

**决策理由：**
- 初期团队规模小，微服务运维成本过高
- 各模块间耦合度可控，通过清晰的接口边界隔离
- 数据管道部分天然适合异步任务队列解耦
- 后期可按需拆分（对话服务、推荐服务、数据管道服务）

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ 学生端    │ │ 管理员端  │ │ 审核工作台 │ │  数据看板         │  │
│  │ (对话+推荐)│ │ (系统管理) │ │ (人工审核) │ │  (可视化监控)     │  │
│  └─────┬────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
└────────┼───────────┼─────────────┼───────────────┼─────────────┘
         │           │             │               │
┌────────┴───────────┴─────────────┴───────────────┴─────────────┐
│                      API 网关层 (Nginx/FastAPI)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ 认证鉴权  │ │ 限流熔断  │ │ 请求路由  │ │  WebSocket管理    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      后端服务层 (Backend)                         │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐  │
│  │  对话服务模块     │ │  推荐分析模块    │ │  数据管道模块     │  │
│  │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌──────────────┐ │  │
│  │ │对话引导智能体 │ │ │ │数据分析智能体 │ │ │ │爬虫调度器     │ │  │
│  │ │心理学话术引擎 │ │ │ │用户画像引擎  │ │ │ │数据过滤智能体 │ │  │
│  │ │对话状态管理  │ │ │ │RAG检索增强  │ │ │ │数据清洗智能体 │ │  │
│  │ │情感分析模块  │ │ │ │推荐排序算法  │ │ │ │数据审核智能体 │ │  │
│  │ └─────────────┘ │ │ └─────────────┘ │ │ │人工审核接口  │ │  │
│  └─────────────────┘ └─────────────────┘ │ └──────────────┘ │  │
│                                          └──────────────────┘  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────┐  │
│  │  知识库模块      │ │  用户数据模块    │ │  系统管理模块     │  │
│  │ 向量数据库/检索引擎│ │ 用户CRUD/加密   │ │ 配置/日志/监控   │  │
│  └─────────────────┘ └─────────────────┘ └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────────┐
│                      数据层 (Data Layer)                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │PostgreSQL │ │  MongoDB │ │  Redis   │ │  Milvus/Chroma   │  │
│  │(结构化数据)│ │(对话/画像)│ │(缓存/队列)│ │  (向量存储)      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────┐ ┌──────────┐                                     │
│  │  MinIO   │ │  Celery  │                                     │
│  │(文件存储) │ │(异步任务) │                                     │
│  └──────────┘ └──────────┘                                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

```
用户登录 → 创建会话 → [对话引导循环]
                            │
                    ┌───────┴────────┐
                    │ 对话引导智能体    │ ← 心理学话术库 + 用户画像(增量更新)
                    │ 多轮深度对话     │
                    └───────┬────────┘
                            │ 产出: 用户画像JSON + 标签向量
                    ┌───────┴────────┐
                    │ 数据分析智能体    │ ← RAG知识库 + 历史录取数据 + 政策文件
                    │ 画像→推荐映射   │
                    └───────┬────────┘
                            │ 产出: 志愿推荐列表 + 置信度 + 引用来源
                    ┌───────┴────────┐
                    │ 前端展示        │ → 用户反馈(收藏/忽略/评分)
                    └───────┬────────┘
                            │ 反馈数据回流 → 推荐模型迭代
```

---

## 三、技术栈选型

### 3.1 总体技术栈

| 层次 | 技术选型 | 选型理由 |
|------|---------|---------|
| **前端框架** | React 18 + TypeScript + Next.js 14 | SSR首屏性能好；TypeScript保证大型项目类型安全；生态丰富 |
| **UI组件库** | Ant Design 5 + Tailwind CSS | 中后台场景成熟方案；Ant Design图表/表格/表单完善 |
| **状态管理** | Zustand | 轻量无boilerplate；比Redux更适合中等复杂度项目 |
| **后端框架** | FastAPI (Python 3.11+) | 原生异步；Pydantic类型校验；AI/ML生态兼容最佳 |
| **LLM编排** | LangChain + LangGraph | 多智能体协作；内置RAG工具链；状态图建模对话流程 |
| **LLM调用** | 多模型路由（DeepSeek/通义千问/GPT-4o） | 成本优化；国内模型中文能力强；关键场景用强模型 |
| **向量数据库** | Milvus (生产) / Chroma (开发) | Milvus性能强、扩展性好；Chroma轻量适合本地开发 |
| **关系数据库** | PostgreSQL 16 + pgvector | 成熟稳定；pgvector支持混合查询 |
| **文档数据库** | MongoDB 7 | 对话记录、用户画像的灵活schema |
| **缓存** | Redis 7 | 会话缓存 + 限流 + 轻量任务队列 |
| **任务队列** | Celery + Redis Broker | Python生态标准方案；成熟稳定 |
| **搜索引擎** | Elasticsearch 8 | 混合检索（全文+向量）；政策文件/院校信息检索 |
| **爬虫框架** | Scrapy + Playwright | Scrapy管整站爬取；Playwright处理JS渲染页面 |
| **对象存储** | MinIO (私有部署) | S3兼容；数据不出域；可切换阿里云OSS |
| **容器化** | Docker + Docker Compose | 统一开发/部署环境 |
| **可观测性** | LangFuse (LLM追踪) + Prometheus + Grafana | LangFuse追踪LLM调用链；Prometheus监控系统指标 |
| **CI/CD** | GitHub Actions | 自动测试+构建 |

### 3.2 为什么这样选型

1. **全Python后端**：AI/ML生态（LangChain, transformers, scikit-learn, pandas）全部原生Python，统一语言降低维护成本
2. **FastAPI > Django**：异步原生支持对LLM调用（IO密集型）至关重要；自动OpenAPI文档方便前后端协作
3. **LangGraph > 自研编排**：对话状态图、条件分支、人工审核节点等场景有成熟抽象，避免重新发明轮子
4. **Milvus > Pinecone**：数据不出域（合规要求）；开源可控；中文社区活跃
5. **MongoDB + PostgreSQL双库**：用户画像和对话日志schema灵活多变适合文档型；录取数据、院校信息结构固定适合关系型

---

## 四、五大智能体详细设计

### 4.1 对话引导智能体 (Conversation Guidance Agent)

**职责**：通过心理学引导对话，挖掘学生显性需求（分数、选科）和隐性需求（兴趣倾向、价值观、家庭期望、性格特征）

**核心能力：**
- 多轮对话状态管理（基于LangGraph状态图）
- 心理学话术选择（共情→探索→聚焦→确认 四阶段）
- 意图识别与槽位填充（需要收集的信息维度）
- 情感感知与对话节奏调整

**对话阶段设计：**

```
阶段1: 建立信任 (Rapport)
  - 话术风格：温暖、开放、非评判
  - 目标：了解学生整体状态，建立对话安全感
  - 示例：对考试结果的看法、对未来的想象

阶段2: 深度探索 (Exploration)
  - 话术风格：引导性提问，避免暗示
  - 目标：挖掘兴趣来源、价值观、隐性偏好
  - 心理学工具：职业兴趣(SDS)、MBTI简化维度、价值观排序
  - 关键槽位：学科兴趣、职业憧憬、地域偏好、家庭影响程度

阶段3: 聚焦澄清 (Focusing)
  - 话术风格：结构化、对比性
  - 目标：在矛盾/模糊处深入澄清，确定优先级
  - 方法：两难选择情境、权重排序、假设性提问

阶段4: 画像确认 (Confirmation)
  - 话术风格：总结性、可视化反馈
  - 目标：输出用户画像草图让学生确认/修正
```

**技术实现：**
- System Prompt设计：心理学专家角色设定 + 四阶段话术模板 + 禁止直接建议（保持中立引导）
- Few-shot示例库：针对不同学生类型（迷茫型、主见型、焦虑型、随性型）的话术示例
- 情感分析：基于文本的情感倾向实时监测，当检测到强烈情绪时调整话术节奏
- 状态机实现：LangGraph StateGraph，节点=阶段，边=阶段转换条件

**产出：**
```json
{
  "user_id": "xxx",
  "profile_version": 3,
  "explicit_info": {
    "score_range": {"min": 580, "max": 620},
    "subjects": ["物理", "化学", "生物"],
    "region": "广东省",
    "batch": "本科批"
  },
  "implicit_profile": {
    "interest_dimensions": {
      "RIASEC_scores": {"R": 3, "I": 8, "A": 6, "S": 7, "E": 4, "C": 5},
      "dominant_types": ["I", "S"]
    },
    "values_ranking": ["个人成长", "社会贡献", "工作稳定性", "薪资水平"],
    "personality_traits": {
      "openness": 0.8, "conscientiousness": 0.7,
      "extraversion": 0.4, "agreeableness": 0.75, "neuroticism": 0.5
    },
    "regional_preference": {"preferred": ["广东", "上海"], "excluded": []},
    "family_influence_level": "medium",
    "career_vision": "希望从事生物医学研究..."
  },
  "confidence_scores": {
    "interest": 0.85,
    "values": 0.70,
    "personality": 0.65
  }
}
```

### 4.2 数据分析智能体 (Data Analysis Agent)

**职责**：基于用户画像+知识库数据，生成个性化志愿推荐与行业前景分析

**核心能力：**
- 用户画像向量化 → 院校/专业匹配
- 成绩-位次-录取概率计算
- 多目标推荐排序（匹配度×录取概率×就业前景×薪资水平）
- 推荐理由可解释性（引用具体数据源）

**推荐流程：**

```
用户画像 → [特征向量化] → 向量检索(相似专业/院校)
                            +
成绩位次 → [位次映射] → 历年录取位次匹配
                            +
地区政策 → [政策规则引擎] → 地域限制/优惠/专项计划
                            +
行业数据 → [前景评分] → 行业增长率/薪资/就业率
                            ↓
                    [多目标排序模型]
                    加权融合 → Top-N推荐列表
                            ↓
                    [推荐解释生成]
                    LLM生成个性化理由 + 数据引用
```

**排序模型设计：**
- 第一阶段：规则过滤（硬性条件：批次线、选科要求、体检限制）
- 第二阶段：向量相似度粗排（Top-500 → Top-100）
- 第三阶段：多因子精排（Top-100 → Top-20）
  - 分数匹配度 (30%)
  - 兴趣匹配度 (25%)
  - 就业前景 (20%)
  - 地域匹配 (15%)
  - 院校层次 (10%)
- 第四阶段：多样性重排（避免同类院校扎堆，保证冲/稳/保梯度）

### 4.3 数据过滤智能体 (Data Filtering Agent)

**职责**：对爬虫原始数据进行初筛，过滤低质量/不可靠/不相关数据

**过滤规则体系：**

1. **硬编码规则层**（快速过滤，不消耗LLM）：
   - 数据源白名单/黑名单（.gov.cn / .edu.cn 优先）
   - 时间有效性（超过N年的数据标记过期）
   - 格式完整性（必需字段检查）
   - 去重（基于内容哈希 + 语义相似度）
   - 内容长度阈值

2. **LLM辅助规则层**（语义理解）：
   - 内容相关性判断（是否与高考志愿相关）
   - 内容类型分类（政策/统计/经验分享/广告）
   - 可信度初评（是否有数据来源引用、发布日期、机构署名）
   - 立场识别（客观陈述 vs 主观意见 vs 营销推广）

**输出：**
```json
{
  "item_id": "xxx",
  "status": "pass" | "reject" | "uncertain",
  "category": "policy" | "statistics" | "admission_data" | "industry_report",
  "reliability_score": 0.85,
  "filter_reason": "..."
}
```

### 4.4 数据清洗智能体 (Data Cleaning Agent)

**职责**：对通过过滤的数据进行格式标准化、缺失字段补全、错误修正

**清洗操作类型：**
- 字段映射标准化（不同来源的院校名称统一 → 教育部标准代码）
- 结构化提取（从HTML/PDF中提取表格数据 → JSON）
- 缺失值处理（标记缺失 or LLM推理补全 or 交叉验证补全）
- 异常值检测与修正
- 数据版本标记（来源URL、抓取时间、清洗时间）

### 4.5 数据审核智能体 (Data Audit Agent)

**职责**：最终质量把关，对清洗后的数据进行可信度终审，标记争议数据供人工复核

**审核维度：**
- 事实一致性：与已有权威数据交叉验证
- 逻辑合理性：数据内部是否存在逻辑矛盾
- 来源权威性：综合评估来源可信度
- 时效性：数据发布/更新时间

**人机协作流程：**
- 置信度 ≥ 0.9：自动通过
- 0.6 ≤ 置信度 < 0.9：标记为"待人工复核"
- 置信度 < 0.6：自动拒绝或降级为"参考数据"

---

## 五、数据管道详细设计

### 5.1 数据源规划

| 数据类别 | 来源示例 | 更新频率 | 优先级 |
|---------|---------|---------|--------|
| 高考政策文件 | 教育部官网、各省教育考试院 | 年度（6月重点关注） | P0 |
| 历年录取数据 | 各省教育考试院、阳光高考 | 年度 | P0 |
| 院校基本信息 | 教育部高校名单、各校官网 | 季度 | P0 |
| 专业目录与介绍 | 教育部专业目录、各校培养方案 | 年度 | P1 |
| 行业薪资数据 | 国家统计局、招聘平台报告 | 季度 | P1 |
| 就业质量报告 | 各高校就业质量年度报告 | 年度 | P1 |
| 行业发展趋势 | 政府规划文件、行业研究报告 | 半年度 | P1 |
| 地区经济数据 | 各省市统计年鉴 | 年度 | P2 |
| 学生经验分享 | 知乎、小红书（低权重参考） | 持续 | P3 |

### 5.2 管道架构

```
爬虫调度器 (APScheduler定时/手动触发)
    │
    ├── Scrapy Spider 1: 政策文件爬虫 (政府网站)
    ├── Scrapy Spider 2: 录取数据爬虫 (教育考试院)
    ├── Scrapy Spider 3: 院校信息爬虫 (高校官网)
    ├── Scrapy Spider 4: 行业数据爬虫 (统计局/招聘平台)
    └── Scrapy Spider 5: 就业报告爬虫 (高校就业网)
            │
            ↓ 原始数据 (raw/)
            │
    ┌───────────────────────────┐
    │  过滤层 (Filtering Layer)  │
    │  - 硬编码规则引擎          │
    │  - 数据过滤智能体          │
    └───────────┬───────────────┘
            │ 通过的数据 (filtered/)
            ↓
    ┌───────────────────────────┐
    │  清洗层 (Cleaning Layer)   │
    │  - 格式标准化              │
    │  - 数据清洗智能体          │
    └───────────┬───────────────┘
            │ 清洗后数据 (cleaned/)
            ↓
    ┌───────────────────────────┐
    │  审核层 (Audit Layer)      │
    │  - 数据审核智能体(粗筛)    │
    │  - 人工审核工作台(精筛)    │
    └───────────┬───────────────┘
            │ 审核通过 (approved/)
            ↓
    ┌───────────────────────────┐
    │  入库 & 向量化             │
    │  - PostgreSQL(结构化)      │
    │  - Milvus(向量嵌入)        │
    │  - Elasticsearch(全文索引) │
    └───────────────────────────┘
```

### 5.3 可视化审核工作台

为人工审核环节设计独立前端页面：

- 待审核数据队列（分页、筛选、排序）
- 数据详情面板（原始 vs 清洗后对比）
- 快速操作：通过/拒绝/修改/标记
- 审核统计（今日审核量、通过率、各来源质量分布）
- 审核历史与追溯

---

## 六、知识库与RAG设计

### 6.1 知识库结构

```
知识库
├── 政策库 (Policy KB)
│   ├── 全国性政策 (教育部文件)
│   ├── 省级政策 (各省考试院文件)
│   └── 专项计划 (强基/专项/定向等)
├── 院校库 (College KB)
│   ├── 院校基础信息 (办学层次/类型/所在地/特色)
│   ├── 学科评估结果
│   └── 历年录取数据(分省/分科/分专业)
├── 专业库 (Major KB)
│   ├── 专业目录与培养方案
│   ├── 专业就业方向
│   └── 专业-行业映射关系
├── 行业库 (Industry KB)
│   ├── 行业发展报告
│   ├── 薪资统计数据
│   └── 人才需求预测
└── 心理学知识库 (Psychology KB)
    ├── 霍兰德(SDS)理论体系
    ├── 职业兴趣-专业映射
    └── 对话引导话术库
```

### 6.2 RAG检索策略

采用**混合检索 + 重排序**方案：

```
用户查询
    │
    ├──→ 向量检索 (Milvus) → 语义相似 Top-K
    │        查询向量由 embedding 模型生成
    │        模型选择: bge-large-zh-v1.5 (中文最优之一)
    │
    └──→ 关键词检索 (Elasticsearch) → BM25精确匹配 Top-K
             针对政策编号、院校代码等精确查询
    │
    ↓ 合并去重 (Reciprocal Rank Fusion)
    │
    ↓ 重排序 (Cross-encoder Reranker)
      模型: bge-reranker-v2-m3
    │
    ↓ Top-N 相关文档
    │
    ↓ 上下文注入 LLM Prompt
```

### 6.3 引用溯源

为确保推荐可靠性，每条推荐必须附带数据引用：

```json
{
  "recommendation": "中山大学 临床医学(5+3一体化)",
  "reasons": [
    {"type": "score_match", "content": "2024年该专业在广东最低录取位次3500名，您的预估位次3200名", "source": "广东省教育考试院2024年录取数据", "source_url": "...", "source_date": "2024-07-20"},
    {"type": "interest_match", "content": "临床医学与您的I型(研究型)和S型(社会型)兴趣高度匹配", "source": "霍兰德职业兴趣理论", "confidence": 0.89},
    {"type": "career_prospect", "content": "临床医学毕业生5年平均薪资位于所有专业前10%", "source": "麦可思2024年中国大学生就业报告", "source_date": "2024-06"}
  ]
}
```

---

## 七、前端设计

### 7.1 页面结构

```
/                          首页(Landing)
/login                     登录页
/register                  注册页
/chat                      对话引导页（核心页面）
/recommendations           志愿推荐结果页
/college/:id               院校详情页
/major/:id                 专业详情页
/industry                  行业前景分析页
/profile                   用户画像页
/settings                  个人设置
/admin/dashboard           管理后台-数据看板
/admin/pipeline            管理后台-数据管道管理
/admin/review              管理后台-人工审核工作台
/admin/knowledge           管理后台-知识库管理
/admin/users               管理后台-用户管理
```

### 7.2 核心页面：对话引导页设计

这是系统的核心交互页面，设计要点：

**布局：** 三栏式（可折叠侧栏）
- 左侧：对话阶段指示器 + 已收集信息概览（槽位填充进度）
- 中间：对话流（消息气泡） + 输入区
- 右侧：实时画像预览面板（随对话逐步填充，可折叠）

**交互特性：**
- 打字机效果：智能体回复逐字呈现
- 思考状态指示：显示"正在分析您的回答..."
- 阶段性小结：每个对话阶段结束时生成可视化小结卡片
- 情绪感知UI：根据对话情绪切换配色（温暖色调/冷静色调）
- 断点续聊：刷新页面后恢复对话上下文

**UI风格：**
- 整体：温暖、专业、值得信赖（避免冷冰冰的科技感）
- 配色：暖白底 + 深蓝主色 + 金色点缀（教育行业联想）
- 字体：系统默认中文字体（苹方/WIndows YaHei），保证可读性
- 动效：微妙过渡动画，不夸张

### 7.3 推荐结果页设计

- 顶部：用户画像摘要卡片
- 筛选栏：院校层次/地区/专业类别/批次 多选筛选
- 结果列表：卡片式布局
  - 每张卡片：院校名+专业、录取概率、匹配度评分、前景评分
  - 展开查看：详细理由+数据来源引用
- 排序选项：综合推荐/录取概率/匹配度/前景
- 对比功能：勾选多所院校并排对比
- 收藏功能：保存到个人志愿草稿表

### 7.4 管理后台设计

- 数据看板：管道运行状态、数据量统计、审核进度
- 数据管道管理：爬虫任务启停、参数配置、运行日志
- 审核工作台：待审队列、详情对比、批量操作

---

## 八、后端接口设计

### 8.1 API设计原则

- RESTful风格，JSON统一返回格式
- 版本化：`/api/v1/...`
- 统一错误格式：`{"code": 40001, "message": "...", "detail": {}}`
- 分页统一参数：`?page=1&page_size=20`
- 认证：JWT Bearer Token

### 8.2 核心接口列表

```
## 认证模块 POST /api/v1/auth
POST   /auth/register              用户注册
POST   /auth/login                  用户登录
POST   /auth/refresh                刷新token
POST   /auth/logout                 登出

## 对话模块 WS /api/v1/chat
WS     /chat/session/{session_id}   WebSocket对话连接
POST   /chat/session                创建新对话会话
GET    /chat/session/{session_id}   获取会话历史
GET    /chat/sessions               获取用户所有会话列表
DELETE /chat/session/{session_id}   删除会话
POST   /chat/session/{session_id}/summarize  触发阶段小结

## 用户画像 GET /api/v1/profile
GET    /profile                     获取当前用户画像
GET    /profile/history             获取画像更新历史
POST   /profile/feedback            提交画像反馈/修正

## 推荐模块 GET /api/v1/recommendation
GET    /recommendations             获取推荐列表
GET    /recommendations/{id}        获取单条推荐详情
POST   /recommendations/{id}/feedback  提交推荐反馈
POST   /recommendations/compare     对比多所院校

## 院校/专业查询 GET /api/v1/reference
GET    /colleges                    院校列表（分页+筛选）
GET    /colleges/{id}               院校详情
GET    /majors                      专业列表
GET    /majors/{id}                 专业详情
GET    /admission/trend             录取趋势数据
GET    /industries                  行业分析数据

## 管理后台 (需管理员权限)
GET    /admin/dashboard/stats       数据看板统计
POST   /admin/pipeline/scrape/trigger   手动触发爬虫
GET    /admin/pipeline/jobs             爬虫任务状态
GET    /admin/review/queue              审核队列
POST   /admin/review/{item_id}/approve  审核通过
POST   /admin/review/{item_id}/reject   审核拒绝
POST   /admin/review/{item_id}/modify   审核修改
GET    /admin/knowledge/stats           知识库统计
POST   /admin/knowledge/reindex         触发重建索引

## 用户管理
GET    /user/settings               获取用户设置
PUT    /user/settings               更新用户设置
GET    /user/favorites              获取收藏列表
POST   /user/favorites              添加收藏
DELETE /user/favorites/{id}         取消收藏
```

### 8.3 WebSocket通信协议（对话）

```json
// 客户端 → 服务端
{
  "type": "message",
  "session_id": "uuid",
  "content": "我觉得自己对生物很感兴趣...",
  "timestamp": 1715500000
}

// 服务端 → 客户端
{
  "type": "message",           // 消息类型: message | thinking | summary | profile_update | error
  "role": "assistant",
  "content": "能具体说说是什么让你对生物产生兴趣的吗？",
  "stage": "exploration",      // 当前对话阶段
  "timestamp": 1715500001
}

// 服务端 → 客户端 (思考状态)
{
  "type": "thinking",
  "message": "正在分析您的兴趣倾向..."
}

// 服务端 → 客户端 (画像增量更新)
{
  "type": "profile_update",
  "field": "interest_dimensions",
  "value": {"biology": 0.8, "chemistry": 0.6},
  "confidence": 0.75
}

// 服务端 → 客户端 (阶段小结)
{
  "type": "summary",
  "stage": "exploration",
  "content": "通过刚才的对话，我了解到...",
  "profile_snapshot": {...}
}
```

---

## 九、数据库设计概要

### 9.1 PostgreSQL 核心表

```sql
-- 用户基础表
users (id, phone, password_hash, region, created_at, updated_at)

-- 用户画像表 (版本化，每次对话后可能更新)
user_profiles (id, user_id, version, profile_json, confidence_json, created_at)

-- 学生成绩信息
student_scores (id, user_id, exam_type, total_score, subject_scores_json, 
                province_rank, source, created_at)

-- 院校信息
colleges (id, name, code, type, level, province, city, website, 
          is_985, is_211, is_double_first_class, introduction, updated_at)

-- 专业目录
majors (id, name, code, category, sub_category, degree, duration, description)

-- 院校-专业-录取数据
admission_data (id, college_id, major_id, year, province, batch, 
                min_score, min_rank, avg_score, max_score, 
                enrollment_count, subject_requirements, source_url)

-- 政策文件
policies (id, title, region, category, publish_date, effective_date,
          content_text, content_vector, source_url, reliability_score)

-- 行业数据
industry_data (id, industry_name, year, avg_salary, employment_rate,
               growth_rate, talent_demand, source_url)

-- 用户收藏
user_favorites (id, user_id, college_id, major_id, created_at)

-- 推荐记录
recommendations (id, user_id, profile_version, recommendation_json, 
                 created_at)

-- 推荐反馈
recommendation_feedback (id, recommendation_id, user_id, feedback_type, 
                         rating, comment, created_at)

-- 数据管道任务
pipeline_jobs (id, spider_name, status, started_at, finished_at, 
               items_collected, items_passed, error_log)

-- 审核记录
review_records (id, data_item_id, reviewer_id, status, comment, 
                reviewed_at)
```

### 9.2 MongoDB 集合

```
conversations: {
  _id, user_id, session_id, 
  messages: [{role, content, stage, timestamp, metadata}],
  current_stage, profile_snapshot,
  created_at, updated_at
}

user_behavior_logs: {
  _id, user_id, action, context, timestamp
}
```

### 9.3 Redis 缓存策略

| Key Pattern | 用途 | TTL |
|-------------|------|-----|
| `session:{token}` | 用户会话 | 7天 |
| `rate_limit:{user_id}:{endpoint}` | 接口限流 | 1分钟 |
| `cache:college:{id}` | 院校信息缓存 | 1小时 |
| `cache:major:{id}` | 专业信息缓存 | 1小时 |
| `dialog_state:{session_id}` | 对话状态快照 | 30分钟 |
| `task:celery:lock:{task_id}` | 任务去重锁 | 5分钟 |

---

## 十、安全架构设计

### 10.1 数据安全

| 安全措施 | 说明 |
|---------|------|
| **传输加密** | 全站HTTPS；WebSocket使用WSS |
| **存储加密** | 用户敏感数据（成绩、手机号、家庭住址）AES-256-GCM加密存储 |
| **密码安全** | bcrypt哈希 + 盐值；密码复杂度要求 |
| **数据脱敏** | 日志中自动脱敏手机号/身份证号；管理后台可配置脱敏级别 |
| **数据隔离** | 用户只能访问自己的数据；管理员按角色授权 |
| **审计日志** | 所有敏感操作记录审计日志（谁、何时、做了什么、IP） |
| **备份策略** | 每日自动备份 + 异地存储 |

### 10.2 合规要求（中国PIPL）

- 用户数据收集前需明确告知并获取同意
- 提供数据导出功能（用户可下载自己的所有数据）
- 提供账号注销+数据删除功能
- 隐私政策页面清晰说明数据用途
- 不出境存储（所有服务器在中国大陆）

### 10.3 API安全

- JWT short-lived access token (15min) + refresh token (7d)
- 接口限流（学生端100req/min, 管理端300req/min）
- 输入校验（Pydantic + 防注入）
- CORS白名单
- 关键接口操作二次确认

---

## 十一、项目文件结构

```
gaokao_agents/
├── README.md                           # 项目简介(面向用户)
├── PROJECT_PLAN.md                     # 本设计方案文档
├── LICENSE
├── .gitignore
├── .env.example                        # 环境变量模板
├── docker-compose.yml                  # 开发环境编排
├── Makefile                            # 常用命令快捷方式
│
├── docs/                               # 开发文档
│   ├── architecture.md                 # 架构详细说明
│   ├── api-specification.md            # API接口文档
│   ├── agent-design.md                 # 智能体设计细节
│   ├── database-schema.md              # 数据库设计
│   ├── deployment.md                   # 部署指南
│   └── psychology-framework.md         # 心理学理论框架说明
│
├── frontend/                           # 前端项目
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── public/
│   │   ├── favicon.ico
│   │   └── assets/                     # 静态资源
│   └── src/
│       ├── app/                        # Next.js App Router
│       │   ├── layout.tsx
│       │   ├── page.tsx                # 首页
│       │   ├── chat/
│       │   │   └── page.tsx            # 对话页
│       │   ├── recommendations/
│       │   │   └── page.tsx            # 推荐结果页
│       │   ├── college/
│       │   │   └── [id]/page.tsx       # 院校详情
│       │   ├── major/
│       │   │   └── [id]/page.tsx       # 专业详情
│       │   ├── industry/
│       │   │   └── page.tsx            # 行业分析
│       │   ├── profile/
│       │   │   └── page.tsx            # 用户画像
│       │   ├── settings/
│       │   │   └── page.tsx            # 设置
│       │   └── admin/                  # 管理后台
│       │       ├── layout.tsx
│       │       ├── dashboard/page.tsx
│       │       ├── pipeline/page.tsx
│       │       ├── review/page.tsx
│       │       ├── knowledge/page.tsx
│       │       └── users/page.tsx
│       ├── components/                 # 通用组件
│       │   ├── chat/
│       │   │   ├── ChatBubble.tsx
│       │   │   ├── ChatInput.tsx
│       │   │   ├── StageIndicator.tsx
│       │   │   ├── ProfilePreview.tsx
│       │   │   └── ThinkingIndicator.tsx
│       │   ├── recommendation/
│       │   │   ├── RecommendationCard.tsx
│       │   │   ├── RecommendationList.tsx
│       │   │   ├── ComparePanel.tsx
│       │   │   └── FilterBar.tsx
│       │   ├── admin/
│       │   │   ├── ReviewQueue.tsx
│       │   │   ├── PipelineMonitor.tsx
│       │   │   └── StatsDashboard.tsx
│       │   └── common/
│       │       ├── Layout.tsx
│       │       ├── Header.tsx
│       │       ├── Sidebar.tsx
│       │       ├── Loading.tsx
│       │       └── ErrorBoundary.tsx
│       ├── hooks/                      # 自定义Hooks
│       │   ├── useChat.ts
│       │   ├── useWebSocket.ts
│       │   ├── useAuth.ts
│       │   └── useRecommendation.ts
│       ├── services/                   # API调用层
│       │   ├── api.ts                  # axios实例 + 拦截器
│       │   ├── auth.ts
│       │   ├── chat.ts
│       │   ├── recommendation.ts
│       │   ├── reference.ts
│       │   └── admin.ts
│       ├── stores/                     # 状态管理(Zustand)
│       │   ├── authStore.ts
│       │   ├── chatStore.ts
│       │   ├── profileStore.ts
│       │   └── recommendationStore.ts
│       ├── utils/                      # 工具函数
│       │   ├── format.ts
│       │   ├── validator.ts
│       │   └── constants.ts
│       └── styles/                     # 全局样式
│           └── globals.css
│
├── backend/                            # 后端项目
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic.ini                     # 数据库迁移
│   ├── Dockerfile
│   ├── main.py                         # FastAPI 入口
│   ├── config.py                       # 配置管理
│   │
│   ├── api/                            # API路由层
│   │   ├── __init__.py
│   │   ├── deps.py                     # 依赖注入
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── chat.py
│   │       ├── profile.py
│   │       ├── recommendation.py
│   │       ├── reference.py
│   │       ├── admin.py
│   │       └── user.py
│   │
│   ├── agents/                         # 智能体模块
│   │   ├── __init__.py
│   │   ├── base.py                     # 智能体基类
│   │   ├── conversation/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # 对话引导智能体
│   │   │   ├── state_machine.py        # 对话状态机(LangGraph)
│   │   │   ├── psychology_engine.py    # 心理学话术引擎
│   │   │   ├── emotion_analyzer.py     # 情感分析
│   │   │   ├── slot_filler.py          # 槽位填充器
│   │   │   └── prompts/               # Prompt模板
│   │   │       ├── system_prompt.py
│   │   │       ├── stage_prompts.py
│   │   │       └── few_shot_examples.py
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # 数据分析智能体
│   │   │   ├── profile_engine.py       # 用户画像构建引擎
│   │   │   ├── matcher.py              # 画像-院校匹配
│   │   │   ├── ranker.py               # 多因子排序
│   │   │   └── explainer.py            # 推荐解释生成
│   │   ├── filter/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # 数据过滤智能体
│   │   │   ├── rule_engine.py          # 硬编码规则引擎
│   │   │   └── rules/                  # 规则配置
│   │   │       ├── source_rules.yaml
│   │   │       └── content_rules.yaml
│   │   ├── cleaning/
│   │   │   ├── __init__.py
│   │   │   ├── agent.py                # 数据清洗智能体
│   │   │   ├── normalizer.py           # 格式标准化
│   │   │   ├── extractor.py            # 结构化提取
│   │   │   └── validator.py            # 数据校验
│   │   └── audit/
│   │       ├── __init__.py
│   │       ├── agent.py                # 数据审核智能体
│   │       └── cross_validator.py      # 交叉验证
│   │
│   ├── knowledge_base/                 # 知识库模块
│   │   ├── __init__.py
│   │   ├── embeddings/
│   │   │   ├── __init__.py
│   │   │   └── embedding_service.py    # 嵌入模型服务
│   │   ├── retrieval/
│   │   │   ├── __init__.py
│   │   │   ├── hybrid_searcher.py      # 混合检索器
│   │   │   └── reranker.py             # 重排序器
│   │   └── vector_store/
│   │       ├── __init__.py
│   │       └── milvus_client.py        # Milvus客户端封装
│   │
│   ├── data_pipeline/                  # 数据管道模块
│   │   ├── __init__.py
│   │   ├── scheduler.py                # 爬虫调度器
│   │   ├── scraper/
│   │   │   ├── __init__.py
│   │   │   ├── base_spider.py
│   │   │   ├── spiders/
│   │   │   │   ├── policy_spider.py
│   │   │   │   ├── admission_spider.py
│   │   │   │   ├── college_spider.py
│   │   │   │   ├── industry_spider.py
│   │   │   │   └── employment_spider.py
│   │   │   └── middleware/
│   │   │       └── anti_ban.py         # 反反爬中间件
│   │   ├── filter/
│   │   │   ├── __init__.py
│   │   │   └── pipeline.py             # 过滤管道
│   │   ├── cleaner/
│   │   │   ├── __init__.py
│   │   │   └── pipeline.py             # 清洗管道
│   │   └── auditor/
│   │       ├── __init__.py
│   │       └── pipeline.py             # 审核管道
│   │
│   ├── models/                         # 数据库模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── profile.py
│   │   ├── college.py
│   │   ├── major.py
│   │   ├── admission.py
│   │   ├── policy.py
│   │   └── pipeline.py
│   │
│   ├── services/                       # 业务服务层
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── chat_service.py
│   │   ├── recommendation_service.py
│   │   └── pipeline_service.py
│   │
│   ├── utils/                          # 工具函数
│   │   ├── __init__.py
│   │   ├── security.py                 # 加密/解密
│   │   ├── jwt.py                      # JWT工具
│   │   ├── pagination.py               # 分页工具
│   │   └── logger.py                   # 日志配置
│   │
│   └── migrations/                     # Alembic数据库迁移
│       └── versions/
│
├── data/                               # 数据目录 (gitignore)
│   ├── raw/                            # 爬虫原始数据
│   ├── filtered/                       # 过滤后数据
│   ├── cleaned/                        # 清洗后数据
│   ├── approved/                       # 审核通过数据
│   └── logs/                           # 运行日志
│
├── scripts/                            # 运维脚本
│   ├── init_db.py                      # 初始化数据库
│   ├── seed_data.py                    # 填充测试数据
│   ├── run_spider.sh                   # 手动运行爬虫
│   └── backup.sh                       # 数据备份
│
├── tests/                              # 测试
│   ├── unit/
│   │   ├── test_conversation_agent.py
│   │   ├── test_analysis_agent.py
│   │   ├── test_filter_agent.py
│   │   ├── test_cleaning_agent.py
│   │   ├── test_audit_agent.py
│   │   └── test_services.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_pipeline.py
│   │   └── test_rag.py
│   └── e2e/
│       └── test_user_flow.py
│
├── docker/                             # Docker配置
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx.conf
│   └── milvus-standalone.yaml
│
└── deploy/                             # 部署配置
    ├── docker-compose.prod.yml
    ├── k8s/                            # Kubernetes (后期)
    └── ansible/                        # Ansible (后期)
```

---

## 十二、开发阶段规划

### Phase 1: MVP (0-3个月)
**目标：** 核心对话+推荐闭环跑通

- [ ] 项目脚手架搭建（前端+后端+Docker）
- [ ] 用户注册/登录/鉴权
- [ ] 对话引导智能体（基础版：4阶段对话+槽位填充）
- [ ] 用户画像构建引擎（基础版）
- [ ] 预置知识库（手动整理100条院校/专业数据）
- [ ] RAG基础检索（Chroma本地向量库）
- [ ] 推荐生成（基础版：规则匹配+简单排序）
- [ ] 对话页面 + 推荐结果页面（基础UI）

### Phase 2: 数据管道建设 (3-6个月)
**目标：** 自动化数据采集与处理链路

- [ ] Scrapy爬虫集群（5个数据源爬虫）
- [ ] 数据过滤/清洗/审核智能体联调
- [ ] 人工审核工作台
- [ ] Milvus向量数据库对接
- [ ] Elasticsearch全文索引
- [ ] 知识库数据规模扩展到10000+条

### Phase 3: 智能优化 (6-9个月)
**目标：** 提升智能体质量与推荐效果

- [ ] 对话引导智能体优化（基于真实对话数据微调prompt）
- [ ] 情感分析模块集成
- [ ] 混合检索+重排序上线
- [ ] 推荐排序模型优化（引入用户反馈信号）
- [ ] 多模型路由（成本优化）
- [ ] A/B测试框架
- [ ] LangFuse全链路追踪

### Phase 4: 完善与扩展 (9-12个月)
**目标：** 系统完善与功能扩展

- [ ] 管理后台完善（数据看板+系统监控）
- [ ] 院校对比功能
- [ ] 志愿表模拟填报
- [ ] 行业前景深度分析报告
- [ ] 移动端适配
- [ ] 性能优化与压测
- [ ] 安全审计与加固
- [ ] 生产环境部署

---

## 十三、关键技术难点与解决方案

| 难点 | 风险等级 | 解决方案 |
|------|---------|---------|
| **心理学对话质量** | 🔴高 | 与心理学专业人士合作设计话术框架；持续收集真实对话数据微调；A/B测试不同话术效果 |
| **推荐结果的可靠性** | 🔴高 | 每条推荐强制附带数据来源引用；建立推荐置信度评分；设计用户反馈闭环 |
| **数据获取合规性** | 🔴高 | 优先使用政府公开数据；爬虫遵守robots.txt；咨询法务确认数据使用边界 |
| **中文语义理解** | 🟡中 | 选用专门的中文embedding模型(bge-large-zh)；中文分词优化；领域词典建设 |
| **RAG检索质量** | 🟡中 | 混合检索策略；定期评估检索效果；人工标注检索对 |
| **多智能体协调** | 🟡中 | LangGraph统一编排；定义清晰的智能体间接口协议；全链路追踪定位问题 |
| **数据时效性** | 🟡中 | 数据版本管理；时效性标签；过期数据自动降权 |
| **冷启动问题** | 🟡中 | 预置高质量种子知识库；手动构建初始画像模板；渐进式画像构建 |
| **系统成本控制** | 🟢低 | 多模型路由（简单对话用小模型）；缓存策略；向量检索用轻量索引 |
| **大规模并发** | 🟢低 | 初期不需要过度设计；异步任务队列解耦；水平扩展预留 |

---

## 十四、风险与应对

1. **政策风险**：高考政策每年可能变化 → 系统设计政策规则引擎，支持热更新
2. **数据风险**：数据源不可控（网站改版/关闭） → 多源交叉验证，数据源健康监控
3. **伦理风险**：AI推荐影响学生人生选择 → 强调"辅助决策"定位，不做绝对性建议，始终保留人工判断空间
4. **法律风险**：学生数据泄露 → 安全架构中的多层加密+审计+合规设计

---

## 十五、成功指标

- 对话完成率（学生完成全部4阶段对话的比例）≥ 70%
- 用户画像准确率（学生自评确认画像准确）≥ 80%
- 推荐接受率（学生收藏/认可推荐）≥ 60%
- 知识库数据可靠性评分（人工抽检）≥ 90%
- 系统可用性 ≥ 99.5%
- API响应时间 P95 < 2s（对话响应 < 3s 含LLM调用）

---

## 附录：开发规范

- 代码风格：Python (Ruff), TypeScript (Prettier + ESLint)
- 提交规范：Conventional Commits
- 分支策略：GitHub Flow (main + feature branches)
- Code Review：所有PR至少1人Review
- 测试覆盖率：核心业务逻辑 ≥ 80%
