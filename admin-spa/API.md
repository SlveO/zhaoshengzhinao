# 招生智脑管理后台 API 接口文档

> 所有 API 路径前缀：`/api/v1`
> 认证方式：Bearer Token（请求头 `Authorization: Bearer <access_token>`）
> 租户标识：请求头 `X-Tenant: <tenant_slug>`

---

## 通用说明

### 认证
除登录接口外，所有接口需要在请求头中携带：
```
Authorization: Bearer <access_token>
X-Tenant: <tenant_slug>
```

### 错误响应格式
```json
{
  "detail": "错误描述信息"
}
```

### HTTP 状态码
| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 token 过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 1. 认证模块

### 1.1 用户登录

```
POST /api/v1/auth/login
```

**请求头**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| X-Tenant | string | 是 | 院校标识（slug），如 `scnu` |

**请求体**：
```json
{
  "username": "string",
  "password": "string"
}
```

**响应体**：
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "user_id": "string",
  "username": "string"
}
```

---

## 2. 工作台

### 2.1 获取工作台汇总数据

```
GET /api/v1/admin/dashboard/summary
```

**请求头**：`X-Tenant`

**响应体**：
```json
{
  "channelSummary": {
    "todayNewLeads": 8562,
    "channels": [
      { "name": "官网", "count": 2350 },
      { "name": "微信公众号", "count": 2189 }
    ]
  },
  "consultationSummary": {
    "total": 1246,
    "aiHandled": 842,
    "humanHandled": 404,
    "avgResponseSeconds": 28,
    "trendData": [120, 135, 98, 160, 142, 155, 170, 145, 180, 162, 190, 175]
  },
  "intentSummary": {
    "intentScore": 78,
    "highIntent": 642,
    "midIntent": 1284,
    "lowIntent": 2163
  },
  "followupProgress": {
    "completionRate": 65,
    "pending": 862,
    "inProgress": 1246,
    "done": 2318
  },
  "news": [
    {
      "date": "5月14日",
      "content": "省份高考政策及志愿填报时间汇总已更新",
      "isNew": true
    }
  ],
  "todos": [
    { "label": "待分配线索", "count": 236 },
    { "label": "未跟进提醒（超24小时）", "count": 128 },
    { "label": "待回访咨询", "count": 91 }
  ]
}
```

**类型定义**：
```typescript
interface DashboardSummary {
  channelSummary: ChannelSummary
  consultationSummary: ConsultationSummary
  intentSummary: IntentSummary
  followupProgress: FollowupProgress
  news: NewsItem[]
  todos: TodoItem[]
}

interface ChannelSummary {
  todayNewLeads: number
  channels: { name: string; count: number }[]
}

interface ConsultationSummary {
  total: number
  aiHandled: number
  humanHandled: number
  avgResponseSeconds: number
  trendData: number[]  // 近12个月/天的趋势数据
}

interface IntentSummary {
  intentScore: number       // 意向评分 0-100
  highIntent: number
  midIntent: number
  lowIntent: number
}

interface FollowupProgress {
  completionRate: number    // 完成率百分比
  pending: number
  inProgress: number
  done: number
}

interface NewsItem {
  date: string
  content: string
  isNew: boolean
}

interface TodoItem {
  label: string
  count: number
}
```

---

## 3. 线索管理

### 3.1 获取线索列表

```
GET /api/v1/admin/leads
```

**请求头**：`X-Tenant`

**查询参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| status | string | 否 | `pending` | 线索状态：`pending`（待处理），`processed`（已处理）|
| sort | string | 否 | `priority` | 排序方式：`priority`（按优先级），`intent`（按意向分），`score`（按分数），`time`（按时间）|
| page | number | 否 | 1 | 页码 |
| page_size | number | 否 | 10 | 每页条数 |

**响应体**：
```json
{
  "items": [
    {
      "id": "A001",
      "name": "学生A",
      "intentScore": 92,
      "province": "广东",
      "subjectType": "物理类",
      "score": 585,
      "major": "电子信息方向",
      "concerns": ["就业去向", "转专业", "录取位次"],
      "phone": "13872415203",
      "priority": "P0",
      "detail": {
        "urgency": "24小时内跟进",
        "reason": "该学生多次追问就业与录取可能性...",
        "profile": "广东 / 物理类 / 585分 / 电子信息方向",
        "coreInterests": "就业去向、转专业政策、近三年录取位次",
        "suggestedAction": "建议招生老师 24 小时内人工跟进。",
        "materials": "电子信息类就业案例、专业培养方案、近三年录取位次说明。"
      }
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 10
}
```

**类型定义**：
```typescript
type Priority = 'P0' | 'P1' | 'P2' | 'P3'

interface LeadItem {
  id: string
  name: string
  intentScore: number
  province: string
  subjectType: string     // "物理类" | "历史类"
  score: number
  major: string
  concerns: string[]
  phone: string
  priority: Priority
  detail: {
    urgency: string
    reason: string
    profile: string
    coreInterests: string
    suggestedAction: string
    materials: string
  }
}

interface LeadListResponse {
  items: LeadItem[]
  total: number
  page: number
  page_size: number
}
```

### 3.2 处理线索

```
PUT /api/v1/admin/leads/:id/process
```

**路径参数**：`id` - 线索 ID

**请求体**：
```json
{
  "method": "已电话联系",
  "note": "备注信息（可选）"
}
```

`method` 可选值：`"已电话联系"` | `"在线对话"` | `"已发材料"` | `"已忽略"`

**响应体**：
```json
{
  "id": "A001",
  "name": "学生A",
  "processedAt": "2026-05-24T10:30:00Z",
  "method": "已电话联系",
  "note": "备注信息"
}
```

### 3.3 更新线索优先级

```
PUT /api/v1/admin/leads/:id/priority
```

**路径参数**：`id` - 线索 ID

**请求体**：
```json
{
  "priority": "P1"
}
```

`priority` 可选值：`"P0"` | `"P1"` | `"P2"` | `"P3"`

**响应体**：同 LeadItem

---

## 4. 咨询管理

### 4.1 获取咨询列表

```
GET /api/v1/admin/consultations
```

**查询参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| status | string | 否 | `""` | 状态筛选：`""`（全部），`"已处理"`，`"待处理"` |
| period | string | 否 | `"today"` | 时间范围：`"today"`，`"7d"`，`"30d"` |
| search | string | 否 | `""` | 搜索关键词（匹配学生姓名、主题） |
| page | number | 否 | 1 | 页码 |
| page_size | number | 否 | 10 | 每页条数 |

**响应体**：
```json
{
  "items": [
    {
      "id": "c1",
      "student": "张同学",
      "profile": "广东·物理类",
      "time": "10:24",
      "duration": "8分钟",
      "topic": "计算机专业就业前景咨询",
      "handler": "AI",
      "status": "已处理"
    }
  ],
  "total": 120,
  "page": 1,
  "page_size": 10
}
```

**类型定义**：
```typescript
interface ConsultationItem {
  id: string
  student: string
  profile: string        // "省份·选科"
  time: string           // "10:24" 或 "昨天 16:20"
  duration: string       // "8分钟"
  topic: string
  handler: 'AI' | '人工'
  status: '已处理' | '待处理'
}

interface ConsultationListResponse {
  items: ConsultationItem[]
  total: number
  page: number
  page_size: number
}
```

---

## 5. 画像看板

### 5.1 获取画像看板数据

```
GET /api/v1/admin/analytics/profile-dashboard
```

**响应体**：
```json
{
  "totalProfiles": 12840,
  "riasecDistribution": [
    { "dimension": "R 现实型", "avgScore": 72, "count": 3200 },
    { "dimension": "I 研究型", "avgScore": 68, "count": 4100 },
    { "dimension": "A 艺术型", "avgScore": 55, "count": 2100 },
    { "dimension": "S 社会型", "avgScore": 60, "count": 2800 },
    { "dimension": "E 企业型", "avgScore": 58, "count": 2600 },
    { "dimension": "C 常规型", "avgScore": 50, "count": 2400 }
  ],
  "valuesDistribution": [
    { "value": "就业前景", "percentage": 35 },
    { "value": "学术氛围", "percentage": 25 },
    { "value": "校园生活", "percentage": 20 },
    { "value": "地理位置", "percentage": 12 },
    { "value": "学费水平", "percentage": 8 }
  ],
  "completenessBreakdown": [
    { "level": "L3", "count": 5200 },
    { "level": "L2", "count": 4100 },
    { "level": "L1", "count": 3540 }
  ],
  "_stub": false
}
```

**类型定义**：
```typescript
interface ProfileDashboard {
  totalProfiles: number
  riasecDistribution: {
    dimension: string    // RIASEC 六维名称
    avgScore: number     // 平均分 0-100
    count: number        // 该维度有数据的用户数
  }[]
  valuesDistribution: {
    value: string        // 价值标签
    percentage: number   // 百分比 0-100
  }[]
  completenessBreakdown: {
    level: string        // 完整度等级：L1(仅基础), L2(部分), L3(完整)
    count: number
  }[]
  _stub?: boolean        // 是否为占位数据
}
```

---

## 6. 洞察分析

### 6.1 获取关键词词云

```
GET /api/v1/admin/analytics/topic-cloud?days=30
```

**查询参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| days | number | 否 | 30 | 统计天数：7, 30, 90 |

**响应体**：
```json
[
  { "word": "计算机", "count": 450 },
  { "word": "就业率", "count": 380 },
  { "word": "电子信息", "count": 350 }
]
```

**类型定义**：
```typescript
interface TopicCloudItem {
  word: string
  count: number
}
```

### 6.2 获取情绪时间线

```
GET /api/v1/admin/analytics/emotion-timeline?days=30
```

**查询参数**：同 6.1

**响应体**：
```json
{
  "timeline": [
    {
      "emotion": "positive",
      "data": [
        { "date": "2026-05-01", "count": 45 },
        { "date": "2026-05-02", "count": 52 }
      ]
    },
    {
      "emotion": "negative",
      "data": [
        { "date": "2026-05-01", "count": 12 },
        { "date": "2026-05-02", "count": 8 }
      ]
    }
  ],
  "dates": ["2026-05-01", "2026-05-02"]
}
```

**类型定义**：
```typescript
interface EmotionTimelineData {
  timeline: {
    emotion: string      // positive | neutral | negative | confused | anxious
    data: { date: string; count: number }[]
  }[]
  dates: string[]
}
```

### 6.3 获取咨询热点

```
GET /api/v1/admin/analytics/hot-questions?days=30
```

**查询参数**：同 6.1

**响应体**：
```json
[
  { "topic": "计算机专业课程设置", "count": 120 },
  { "topic": "近三年录取分数线", "count": 98 }
]
```

**类型定义**：
```typescript
interface HotQuestionItem {
  topic: string
  count: number
}
```

---

## 7. 招生报告

### 7.1 获取策略报告

```
GET /api/v1/admin/reports/strategy?view=weekly&period=2026-05
```

**查询参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| view | string | 是 | `weekly` | 视角：`weekly`（本周总览），`content`（内容优化），`lecture`（宣讲重点），`channel`（渠道建议）|
| period | string | 否 | - | 周期，如 `2026-05` |

**响应体**：
```json
{
  "concerns": [
    { "rank": 1, "title": "就业去向咨询上升", "desc": "电子信息类、计算机方向的就业去向持续被追问。" }
  ],
  "gaps": [
    { "rank": 1, "title": "电子信息类就业案例不足", "desc": "现有材料对就业去向说明不够具体。" }
  ],
  "actions": [
    { "rank": 1, "title": "发布《电子信息类专业就业去向解析》推文", "desc": "用真实去向回应就业顾虑。", "priority": "P0" }
  ]
}
```

**类型定义**：
```typescript
type ActionPriority = 'P0' | 'P1' | 'P2'

interface ReportEntry {
  rank: number
  title: string
  desc: string
}

interface ActionEntry extends ReportEntry {
  priority: ActionPriority
}

interface PerspectiveData {
  concerns: ReportEntry[]
  gaps: ReportEntry[]
  actions: ActionEntry[]
}
```

### 7.2 保存策略报告

```
PUT /api/v1/admin/reports/strategy?view=weekly
```

**查询参数**：`view`（必填，同上）

**请求体**：同 PerspectiveData

**响应体**：同 PerspectiveData

### 7.3 获取报告历史版本

```
GET /api/v1/admin/reports/strategy/versions?view=weekly
```

**查询参数**：`view`（必填，同上）

**响应体**：
```json
[
  {
    "label": "系统建议",
    "time": "2026-05-21 09:30",
    "data": { "concerns": [...], "gaps": [...], "actions": [...] }
  },
  {
    "label": "保存记录 #1",
    "time": "2026-05-19 14:42",
    "data": { "concerns": [...], "gaps": [...], "actions": [...] }
  }
]
```

**类型定义**：
```typescript
interface ReportVersion {
  label: string
  time: string      // "YYYY-MM-DD HH:mm"
  data: PerspectiveData
}
```

---

## 8. 渠道管理

### 8.1 获取渠道汇总数据

```
GET /api/v1/admin/channels/summary?period=today
```

**查询参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| period | string | 否 | `today` | 时间范围：`today`, `7d`, `30d` |

**响应体**：
```json
[
  {
    "name": "官网",
    "icon": "🌐",
    "leads": 2350,
    "conversionRate": "12.6%",
    "change": "+3.2%",
    "up": true,
    "pct": 60
  }
]
```

**类型定义**：
```typescript
interface ChannelSummary {
  name: string
  icon: string
  leads: number
  conversionRate: string
  change: string
  up: boolean        // 转化率是否上升
  pct: number        // 进度条百分比（用于前端显示）
}
```

---

## 9. 知识库

### 9.1 获取知识库文档列表

```
GET /api/v1/admin/knowledge/documents
```

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| search | string | 否 | 搜索关键词（匹配标题）|
| type | string | 否 | 文档类型筛选 |
| page | number | 否 | 页码，默认 1 |
| page_size | number | 否 | 每页条数，默认 10 |

文档类型可选值：`admission_score`（录取分数），`curriculum`（课程信息），`employment`（就业数据），`campus_life`（校园生活）

**响应体**：
```json
{
  "documents": [
    {
      "id": "d001",
      "title": "2025年广东省录取分数线",
      "data_type": "admission_score",
      "year": 2025,
      "indexed_at": "2026-05-20T08:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 10
}
```

**类型定义**：
```typescript
interface DocumentItem {
  id: string
  title: string
  data_type: string       // admission_score | curriculum | employment | campus_life
  year: number | null
  indexed_at: string | null   // ISO 8601 时间字符串，null 表示未索引
}

interface KnowledgeDocumentListResponse {
  documents: DocumentItem[]
  total: number
  page: number
  page_size: number
}
```

### 9.2 上传文档

```
POST /api/v1/admin/knowledge/documents
```

**请求格式**：`multipart/form-data`

**表单字段**：
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 文档文件（PDF/DOCX/TXT等） |
| title | string | 否 | 文档标题，默认使用文件名 |
| data_type | string | 是 | 文档类型 |
| year | number | 否 | 数据年份 |

**响应体**：同 DocumentItem

### 9.3 删除文档

```
DELETE /api/v1/admin/knowledge/documents/:id
```

**路径参数**：`id` - 文档 ID

**响应体**：
```json
{
  "success": true
}
```

---

## 10. 品牌配置

### 10.1 获取品牌配置

```
GET /api/v1/admin/brand-config
```

**响应体**：
```json
{
  "name": "华南师范大学",
  "short_name": "SCNU",
  "primary_color": "#2563eb",
  "secondary_color": "#f59e0b",
  "logo_url": "https://cdn.example.com/logo.png",
  "favicon_url": null,
  "login_bg_url": null,
  "welcome_text": "欢迎来到华南师范大学招生咨询平台！"
}
```

### 10.2 更新品牌配置

```
PUT /api/v1/admin/brand-config
```

**请求体**：同 BrandConfig（支持部分更新，传入的字段覆盖，未传入的保持不变）

**类型定义**：
```typescript
interface BrandConfig {
  name: string              // 院校全称
  short_name: string        // 院校简称
  primary_color: string     // 主题色 hex，如 "#2563eb"
  secondary_color: string   // 辅助色 hex
  logo_url: string          // Logo 图片 URL
  favicon_url: string | null
  login_bg_url: string | null   // 登录页背景图
  welcome_text?: string
}
```

---

## 11. AI 对话配置

### 11.1 获取 AI 配置

```
GET /api/v1/admin/ai-persona
```

**响应体**：
```json
{
  "custom_prompt": "你是一位专业、热情的招生咨询助手，代表{tenant_name}招生办...",
  "style": "casual",
  "proactive_recommend": true
}
```

**类型定义**：
```typescript
interface PersonaConfig {
  custom_prompt: string       // 自定义提示词，支持占位符
  style: 'casual' | 'formal'  // 对话风格
  proactive_recommend: boolean // 是否主动推荐
}
```

**提示词占位符说明**：
| 占位符 | 替换内容 |
|--------|----------|
| `{tenant_name}` | 院校名称 |
| `{stage}` | 当前咨询阶段 |
| `{slots_summary}` | 已收集的学生信息摘要 |
| `{style}` | 对话风格（亲切自然的语气 / 正式专业的语气）|

### 11.2 更新 AI 配置

```
PUT /api/v1/admin/ai-persona
```

**请求体**：同 PersonaConfig

**响应体**：同 PersonaConfig

---

## 12. 租户配置

### 12.1 获取租户配置

```
GET /api/v1/admin/tenants/me/config
```

**响应体**：
```json
{
  "brand": { "name": "华南师范大学", "short_name": "SCNU", "..." },
  "modules": {
    "funnel": true,
    "profile_dashboard": true,
    "topic_cloud": true,
    "knowledge": true,
    "brand": true,
    "agent": true,
    "recommendation": true,
    "reports": true,
    "multi_department": false,
    "role_management": false
  },
  "knowledge_base": {
    "doc_count": 42,
    "last_updated": "2026-05-20T08:00:00Z"
  }
}
```

### 12.2 更新模块开关

```
PUT /api/v1/admin/tenants/me/config
```

**请求体**：
```json
{
  "modules": {
    "funnel": true,
    "profile_dashboard": false,
    "topic_cloud": true
  }
}
```

> 支持部分更新，只传需要修改的模块 key

**响应体**：同 12.1 的完整租户配置

**模块 key 定义**：
| Key | 名称 | 说明 | 依赖 |
|-----|------|------|------|
| `funnel` | 招生漏斗 | 分析从访问到报考的全链路转化 | - |
| `profile_dashboard` | 画像看板 | 学生兴趣画像与价值观分布 | - |
| `topic_cloud` | 增强分析 | 词云、情绪时间线、咨询热点 | - |
| `knowledge` | 知识库 | 院校专属知识文档管理 | - |
| `brand` | 品牌配置 | 院校品牌色、Logo、欢迎语 | - |
| `agent` | AI 对话 | 智能体提示词、风格与主动推荐 | - |
| `recommendation` | 专业推荐 | 基于画像的专业匹配推荐 | profile_dashboard |
| `reports` | 招生报告 | 招生优化报告生成中心 | funnel, topic_cloud |
| `multi_department` | 多院系管理 | 多院系数据分权管理 | knowledge |
| `role_management` | 角色权限 | 细粒度角色与权限控制 | multi_department |

---

## 13. 品牌配置（公开，无需认证）

### 13.1 获取登录页品牌配置

```
GET /api/v1/admin/brand-config
```

> 登录页可用此接口获取品牌信息，`X-Tenant` 头通过 URL 参数 `?tenant=slug` 传入

**响应体**：同 BrandConfig（见 10.1）
