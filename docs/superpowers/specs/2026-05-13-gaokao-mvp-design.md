# 高考志愿填报系统 — MVP 设计方案

## 一、目标与范围

### 1.1 目标
5 天内交付一个可让真实学生测试的核心闭环：注册登录 → 心理学引导对话 → 用户画像构建 → 志愿推荐。

### 1.2 范围

**含：**
- 极简注册登录（用户名 + 密码）
- 4 阶段心理学引导对话（WebSocket）
- 用户画像构建（RIASEC + 价值观 + 地域偏好）
- RAG 语义匹配（Chroma + bge-large-zh）
- 志愿推荐列表 + 详情 + 数据来源引用
- 广东省内约 20 所院校、60-80 条录取数据（种子数据手动整理）
- 单机 Docker Compose 部署到云服务器

**不含：**
- 管理后台、审核工作台、数据看板
- 爬虫、数据管道、异步任务
- 情感分析、打字机效果、情绪换色
- 院校对比、收藏功能、推荐反馈闭环
- 多模型路由、下载推荐报告

---

## 二、技术栈

| 层 | 选型 |
|---|---|
| 前端 | Vite + React 18 + TypeScript + Tailwind CSS |
| 后端 | FastAPI (Python 3.11+) |
| LLM 编排 | LangChain + LangGraph |
| LLM | DeepSeek API（前期 Prompt 工程，后期可微调） |
| 关系数据库 | PostgreSQL 16 |
| 缓存/会话 | Redis 7 |
| 向量库 | Chroma（内嵌模式，FastAPI 进程内运行，不需独立容器） |
| Embedding | bge-large-zh-v1.5 |
| 部署 | Docker Compose → 云服务器 |

---

## 三、系统架构

```
┌──────────────────────────────────────────────┐
│              前端 (Vite + React)              │
│  / → /login → /register → /chat →            │
│  /recommendations                             │
└──────────────────┬───────────────────────────┘
                   │ HTTP + WebSocket
┌──────────────────┴───────────────────────────┐
│              FastAPI 进程                      │
│                                                │
│  /api/v1/auth/*    认证路由                    │
│  /api/v1/chat/     对话 WebSocket + REST       │
│  /api/v1/recommend 推荐接口                    │
│  /api/v1/profile   画像接口                    │
│  /api/v1/colleges  院校查询                    │
│                                                │
│  ┌──────────────────────────────────────┐     │
│  │ ConversationAgent (LangGraph 状态机)  │     │
│  │ → DeepSeek API                       │     │
│  └──────────────────────────────────────┘     │
│  ┌──────────────────────────────────────┐     │
│  │ RecommendationService                 │     │
│  │ → Chroma (内嵌) + PostgreSQL          │     │
│  └──────────────────────────────────────┘     │
└──────────────┬────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───┴───┐          ┌──────┴──────┐
│PostgreSQL│       │    Redis     │
│ (主库)    │       │ (会话+缓存)  │
└──────────┘       └─────────────┘
```

---

## 四、前端设计

### 4.1 页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | Landing | 首页介绍 + 跳转登录 |
| `/login` | 登录 | 用户名 + 密码 |
| `/register` | 注册 | 用户名 + 密码 + 地区 + 分数 + 选科 |
| `/chat` | 对话引导 | 核心页面：两栏布局 |
| `/recommendations` | 推荐结果 | 卡片列表 + 展开详情 |

### 4.2 对话引导页 `/chat`

**布局：** 两栏，左侧面板可折叠。
- **左侧**（~280px）：4 步阶段进度条 + 已收集信息槽位逐个亮起 + 完成度百分比
- **右侧**：聊天流 + 思考状态动画 + 输入框

**配色：** 蓝色主调（#4f8cf7），AI 消息左对齐灰底，用户消息右对齐蓝底。

**交互：**
- 页面加载自动连接 WebSocket，恢复上次对话上下文
- 新对话 AI 先开口破冰
- 槽位实时更新，不等阶段结束

**阶段小结弹窗：**
- 每阶段完成时弹出覆盖层，背景变暗模糊
- 卡片展示本阶段收集的画像维度，每项有"修改"按钮
- 修改交互混合：简单项（地域勾选/价值观排序）弹窗内编辑；复杂项（兴趣类型不准确）关闭弹窗回到聊天由 AI 追问引导
- 操作："我再看一下对话"（关闭弹窗）、"确认，进入下一阶段"

### 4.3 推荐结果页 `/recommendations`

**顶部：** 画像摘要条（分数/兴趣/地域三列 + "修改画像"链接回 /chat）

**筛选栏：** 院校层次 / 地区 / 类别 下拉筛选

**卡片列表：**
- 左侧色条：红 = 冲刺 / 绿 = 稳妥 / 蓝 = 保底
- 默认显示：院校名、专业名、层次标签、综合匹配百分比、三条进度条（录取概率/兴趣匹配/前景评分）
- 点击"展开详细理由"：显示三条推荐依据，每条标注来源、URL、数据日期

---

## 五、后端设计

### 5.1 对话智能体

**状态机（LangGraph StateGraph）：**

```
[OPEN] 建立信任 → [EXPLORE] 深度探索 → [FOCUS] 聚焦澄清 → [CONFIRM] 画像确认 → [DONE]
```

| 阶段 | 目标 | 必填槽位 | 话术风格 |
|------|------|---------|---------|
| 建立信任 | 破冰，了解整体状态 | 分数、选科、批次 | 温暖开放，非评判 |
| 深度探索 | 挖掘兴趣/价值观/偏好 | RIASEC 倾向、价值观排序、地域偏好 | 引导性提问，不暗示 |
| 聚焦澄清 | 解决矛盾，确定优先级 | 兴趣-价值观一致性校验 | 结构化对比 |
| 画像确认 | 输出画像让学生确认 | 用户确认标记 | 总结反馈 |

**实现方案：**
- System Prompt：心理学专家角色 + 四阶段话术模板 + 禁止直接建议
- Few-shot 示例库：针对迷茫型/主见型/焦虑型学生
- 槽位填充器：从用户每句话增量提取信息，更新画像

### 5.2 WebSocket 消息协议

```
客户端 → 服务端：{ "type": "message", "session_id": "uuid", "content": "..." }
服务端 → 客户端：
  { "type": "message", "role": "assistant", "content": "...", "stage": "exploration" }
  { "type": "thinking", "message": "正在分析你的回答..." }
  { "type": "stage_change", "from": "exploration", "to": "focusing" }
  { "type": "profile_update", "field": "interest", "value": {...}, "confidence": 0.75 }
  { "type": "summary", "stage": "exploration", "content": "...", "profile_snapshot": {...} }
```

### 5.3 RAG 检索流程

```
用户画像向量 → Chroma 语义检索 Top-30 →
规则过滤（选科/批次/位次）→ Top-15 →
DeepSeek API 精排 + 理由生成 → Top-10 推荐
```

### 5.4 推荐排序

1. 规则过滤：硬性条件（批次线、选科要求）
2. 向量相似度粗排：30 条
3. 规则过滤：15 条
4. LLM 重排序：10 条，同时生成推荐理由和数据引用

排序因子权重：分数匹配 30% + 兴趣匹配 25% + 就业前景 20% + 地域匹配 15% + 院校层次 10%

---

## 六、数据库设计

### 6.1 PostgreSQL 核心表

```sql
users (id, username, password_hash, region, score, subjects, batch, created_at, updated_at)
user_profiles (id, user_id, version, profile_json, confidence_json, created_at)
colleges (id, name, code, type, level, province, city, intro, updated_at)
admission_data (id, college_id, major_name, year, batch, min_score, min_rank, subject_requirements, source_url)
recommendations (id, user_id, profile_version, result_json, created_at)
```

### 6.2 Redis 缓存策略

| Key | 用途 | TTL |
|-----|------|-----|
| `session:{user_id}` | JWT 用户会话 | 7d |
| `dialog_state:{session_id}` | 对话状态快照 | 30min |
| `rate_limit:{user_id}` | 接口限流 | 1min |

---

## 七、种子数据

**范围：** 广东省内热门院校，覆盖 985、211、双一流、省重点各层次。

**每所学校包含：** 基本信息（名称/代码/层次/所在地）+ 3-5 个主干专业 × 历年录取数据（年份/批次/最低分/最低位次/选科要求/来源URL）。

**目标数量：** ~20 所院校，60-80 条 admission_data。

---

## 八、部署

- 云服务器（阿里云/腾讯云轻量应用服务器）
- Docker Compose 单机编排，服务：FastAPI + PostgreSQL + Redis
- Chroma 内嵌在 FastAPI 进程中，不需要独立容器
- 环境变量管理敏感配置（DeepSeek API Key、JWT Secret、数据库密码）

---

## 九、多 Session 并行开发策略

5 天时间，利用多个独立 session 并行推进。拆分原则：每个 session 有独立任务、独立文件、明确的产物和接口边界，互不阻塞。

### 9.1 并行拆分方案

| Session | 任务 | 依赖 | 产出 |
|---------|------|------|------|
| **S1: 基础设施** | 项目脚手架、Docker Compose、数据库建表、种子数据整理、认证模块 | 无 | FastAPI 入口 + PostgreSQL 表结构 + JWT 认证 + 种子数据 JSON |
| **S2: 对话智能体** | LangGraph 状态机 + System Prompt + Few-shot + WebSocket + 槽位填充 | S1 的数据库模型 | 对话 WebSocket 端点 + 画像增量更新 |
| **S3: 推荐系统** | Chroma 嵌入 + RAG 检索 + 排序 + 推荐解释 + `/api/v1/recommend` | S1 的数据库模型 + S1 的种子数据 | 推荐列表接口 + 推荐理由 + 数据来源 |
| **S4: 前端** | 全部 5 个页面 + WebSocket 客户端 + API 调用层 + 状态管理 | 不依赖其他 session（可独立开发，联调前用 mock API） | 前端可运行，mock API 下全流程可用 |

### 9.2 并行时序

```
Day 1-2:  S1 基础设施 (blocker，优先完成)
Day 2-3:  S2 对话智能体 + S3 推荐系统 + S4 前端 (并行启动)
Day 4:    前后端联调 + S2/S3/S4 集成
Day 5:    端到端测试 + 找学生测 + 部署上云
```

### 9.3 Session 间接口约定

**S1 → S2 / S3（数据库模型）：** `user.py`、`profile.py`、`college.py`、`admission.py` 模型定义。S1 完成后提交，S2、S3 基于同一 commit 开发。

**S4 → 后端（API 契约）：** S4 先用 MSW 或 mock 数据开发，API 接口格式预先约定：
- `POST /api/v1/auth/register` — `{username, password, region, score, subjects}`
- `POST /api/v1/auth/login` — `{username, password}` → `{access_token, refresh_token}`
- `WS /api/v1/chat/session/{session_id}` — 消息协议见 5.2
- `GET /api/v1/recommendations` — `{recommendations: [...], profile_snapshot: {...}}`

---

## 十、API 接口简表（MVP）

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
WS     /api/v1/chat/session/{session_id}
POST   /api/v1/chat/session
GET    /api/v1/chat/session/{session_id}
GET    /api/v1/profile
POST   /api/v1/profile/feedback
GET    /api/v1/recommendations
GET    /api/v1/recommendations/{id}
GET    /api/v1/colleges
GET    /api/v1/colleges/{id}
```

---

## 十一、成功标准

- 学生完成 4 阶段对话全程比例 ≥ 60%
- 推荐列表包含冲/稳/保梯度
- 每条推荐可追溯到具体数据来源
- 种子数据覆盖广东省 985/211/双一流/省重点 4 个层次
- 5 天内可以在云服务器上让学生访问
