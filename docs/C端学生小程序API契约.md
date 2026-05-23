# C 端学生小程序 API 契约文档

> 项目：国创赛「招生智脑」  
> 端：C 端学生手机端 / 小程序端  
> 阶段：第一阶段前端页面 + mock 演示 + API 契约校准  
> 依据：README.md、CONVENTIONS.md、mini-app/src/utils/api.ts、mini-app/src/utils/config.ts、mini-app/src/utils/websocket.ts、mini-app/src/stores/chat.ts、mini-app/src/pages.json

本文档中的“已有前端封装”不等于后端接口已完成，后端是否实现需以后端同学确认为准。

---

## 1. C 端第一阶段功能边界

第一阶段只做四个核心模块：

1. AI 招生咨询聊天页
2. 学生画像
3. 本校专业推荐 / 报考建议
4. 本校专业对比 / 意向专业分析

### 1.1 C 端单校约束

当前 C 端小程序不是面向学生的多院校对比平台，而是部署在购买产品高校公众号里的“单高校招生智能咨询小程序”。

当前小程序运行在某一高校租户下，所有回答、推荐、分析都必须限定在当前 `tenant` 对应高校范围内。

学生打开小程序后，只能咨询当前高校相关内容，例如：

- 本校招生政策
- 本校专业介绍
- 本校录取评估
- 本校校园生活
- 本校培养方向
- 本校招生联系方式

C 端第一阶段不得展示：

- 跨院校对比
- 推荐其他高校
- 多学校冲稳保
- 加入院校对比
- 引导学生去看别的学校

第一阶段目标是：

- C 端页面可以完整演示；
- 后端 / WebSocket 暂不可用时，前端可以使用 mock 数据；
- 不新增复杂业务；
- API 路径、请求参数、返回字段先与项目已有规范对齐；
- 所有推荐、对比、分析都限定在当前租户高校内；
- 后端后续可按本文档补充数据库表和真实接口。

---

## 2. 统一请求约定

### 2.1 Base URL

项目统一 API 前缀：

```txt
/api/v1
```

开发环境前端实际请求地址：

```txt
http://localhost:8000/api/v1
```

生产环境前端实际请求地址：

```txt
/api/v1
```

### 2.2 请求头

学生端接口必须携带：

```txt
X-Tenant: <tenantSlug>
Content-Type: application/json
```

如果本地存在登录 token，则额外携带：

```txt
Authorization: Bearer <token>
```

### 2.3 租户

当前小程序从 `tenant.config` 中读取：

```ts
TENANT_SLUG = tenantConfig.tenantSlug
```

演示环境一般使用：

```txt
scnu
```

租户约束说明：

- `X-Tenant` 决定当前小程序属于哪一所高校；
- 聊天回复、画像分析、专业推荐、专业对比都必须在该高校租户范围内完成；
- 后端不得返回其他高校的名称、专业、录取数据或跳转引导；
- 前端 mock 数据也必须只使用当前高校数据。

---

## 3. 统一返回格式

所有 HTTP API 返回统一格式：

```ts
interface ApiResponse<T = unknown> {
  data: T | null
  error: ApiError | null
}

interface ApiError {
  code: string
  message: string
}
```

成功示例：

```json
{
  "data": {
    "session_id": "session_001",
    "guest": true
  },
  "error": null
}
```

失败示例：

```json
{
  "data": null,
  "error": {
    "code": "RATE_LIMIT",
    "message": "请求过于频繁，请稍后再试"
  }
}
```

说明：下文每个接口中的“返回字段”默认指 `data` 内部字段。

---

## 4. 当前 C 端已有页面路径

| 模块 | 页面路径 | 说明 |
|---|---|---|
| AI 招生咨询聊天页 | `pages/chat/index` | 学生与当前高校 AI 招生咨询助手对话入口 |
| 推荐结果 | `pages/recommendations/index` | 展示当前高校内的专业推荐 / 报考建议 |
| 专业分析 | `pages/compare/index` | 展示当前高校内多个意向专业对比，不做跨院校对比 |
| 我的画像 | `pages/profile/index` | 展示学生画像 |

说明：`pages/compare/index` 作为已有页面路径可保留，但产品含义需要从“跨院校对比”调整为“本校专业对比 / 意向专业分析”。

---

## 5. 聊天模块 API

### 5.1 创建聊天会话

| 项 | 内容 |
|---|---|
| 接口名称 | 创建聊天会话 |
| 请求方法 | `POST` |
| 接口路径 | `/api/v1/chat/session` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 可以。后端不可用时前端生成 mock session id |

#### 前端传入参数

第一阶段无需请求体。

```ts
interface CreateChatSessionRequest {}
```

#### 后端返回字段

```ts
interface CreateChatSessionData {
  session_id: string
  guest: boolean
}
```

#### 完整返回示例

```ts
type CreateChatSessionResponse = ApiResponse<CreateChatSessionData>
```

```json
{
  "data": {
    "session_id": "session_mock_001",
    "guest": true
  },
  "error": null
}
```

---

### 5.2 WebSocket 聊天连接

| 项 | 内容 |
|---|---|
| 协议 | `WebSocket` |
| 连接路径 | `/api/v1/chat/session/{sessionId}?tenant={tenantSlug}` |
| 示例 | `/api/v1/chat/session/session_mock_001?tenant=scnu` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 可以。后端不可用时前端本地延迟返回 AI 消息 |

WebSocket 聊天协议可以保留，但后端生成回复时必须遵守单校约束：回复内容只能围绕当前 `tenant` 对应高校，不得主动推荐其他高校或生成跨院校比较结论。

#### Client -> Server

发送用户消息：

```ts
interface WsClientMessage {
  type: "message"
  content: string
}
```

```json
{
  "type": "message",
  "content": "我对计算机和人工智能比较感兴趣，想了解本校有哪些专业适合我？"
}
```

心跳消息：

```ts
interface WsClientPing {
  type: "ping"
}
```

```json
{
  "type": "ping"
}
```

#### Server -> Client

AI 正在思考：

```ts
interface WsThinkingMessage {
  type: "thinking"
}
```

AI 回复消息：

```ts
interface WsAssistantMessage {
  type: "message"
  content: string
  stage?: ChatStage
}

type ChatStage = "explore" | "focus" | "confirm" | "done"
```

画像更新：

```ts
interface WsProfileUpdateMessage {
  type: "profile_update"
  riasec?: Record<string, number>
  values?: string[]
  confidence?: number
  completeness?: "L1" | "L2" | "L3"
}
```

阶段变化：

```ts
interface WsStageChangeMessage {
  type: "stage_change"
  from: ChatStage
  to: ChatStage
}
```

对话总结：

```ts
interface WsSummaryMessage {
  type: "summary"
  content: string
  profile_snapshot?: ProfileSnapshot
}
```

错误消息：

```ts
interface WsErrorMessage {
  type: "error"
  code: string
  message: string
}
```

统一类型：

```ts
type WsServerMessage =
  | WsThinkingMessage
  | WsAssistantMessage
  | WsProfileUpdateMessage
  | WsStageChangeMessage
  | WsSummaryMessage
  | WsErrorMessage
```

---

### 5.3 获取会话历史

| 项 | 内容 |
|---|---|
| 接口名称 | 获取会话历史 |
| 请求方法 | `GET` |
| 接口路径 | `/api/v1/chat/session/{sessionId}` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 第一阶段可以暂不调用 |

#### 前端传入参数

路径参数：

```ts
interface GetChatSessionPathParams {
  sessionId: string
}
```

#### 后端返回字段

```ts
interface ChatMessage {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  stage?: ChatStage
  timestamp: number
}

interface ChatSessionData {
  session_id: string
  guest: boolean
  messages: ChatMessage[]
  profile_snapshot?: ProfileSnapshot
  summary?: string
}
```

#### 完整返回示例

```ts
type GetChatSessionResponse = ApiResponse<ChatSessionData>
```

---

### 5.4 删除会话

| 项 | 内容 |
|---|---|
| 接口名称 | 删除会话 |
| 请求方法 | `DELETE` |
| 接口路径 | `/api/v1/chat/session/{sessionId}` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 第一阶段可以只清空前端状态 |

#### 前端传入参数

```ts
interface DeleteChatSessionPathParams {
  sessionId: string
}
```

#### 后端返回字段

```ts
interface DeleteChatSessionData {
  success: boolean
}
```

---

## 6. 学生画像 API

### 6.1 获取学生画像

| 项 | 内容 |
|---|---|
| 接口名称 | 获取学生画像 |
| 请求方法 | `GET` |
| 接口路径 | `/api/v1/profiles` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 可以。第一阶段前端先 mock 展示学生信息卡和画像结果 |

#### 前端传入参数

第一阶段无需参数，后端根据 token / guest session / tenant 判断当前学生。

```ts
interface GetProfileRequest {}
```

#### 后端返回字段

```ts
interface StudentBasicInfo {
  province: string
  subject_type: "物理类" | "历史类" | string
  score: number
  intent_majors: string[]
}

interface ProfileSnapshot {
  riasec: Record<string, number>
  values: string[]
  confidence: number
  completeness: "L1" | "L2" | "L3"
}

interface StudentProfileData {
  student: StudentBasicInfo
  profile: ProfileSnapshot
  updated_at: string
}
```

#### 完整返回示例

```ts
type GetProfileResponse = ApiResponse<StudentProfileData>
```

```json
{
  "data": {
    "student": {
      "province": "广东",
      "subject_type": "物理类",
      "score": 585,
      "intent_majors": ["计算机", "人工智能"]
    },
    "profile": {
      "riasec": {
        "R": 4,
        "I": 8,
        "A": 5,
        "S": 4,
        "E": 6,
        "C": 3
      },
      "values": ["技术成长", "就业前景", "城市发展"],
      "confidence": 0.76,
      "completeness": "L2"
    },
    "updated_at": "2026-05-23T10:00:00Z"
  },
  "error": null
}
```

说明：`province`、`subject_type`、`score`、`intent_majors` 是 C 端第一阶段页面展示所需字段。画像数据用于后台招生数据分析和线索转化，也用于本校专业推荐 / 报考建议。

---

### 6.2 提交画像反馈

| 项 | 内容 |
|---|---|
| 接口名称 | 提交画像反馈 |
| 请求方法 | `POST` |
| 接口路径 | `/api/v1/profiles/feedback` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 第一阶段可暂不做真实提交 |

#### 前端传入参数

当前前端封装已有：

```ts
interface SubmitProfileFeedbackRequest {
  dimension: string
  score: number
}
```

#### 后端返回字段

```ts
interface SubmitProfileFeedbackData {
  success: boolean
}
```

---

## 7. 本校专业推荐 / 报考建议 API

### 7.1 获取本校专业推荐 / 报考建议

| 项 | 内容 |
|---|---|
| 接口名称 | 获取本校专业推荐 / 报考建议 |
| 请求方法 | `GET` |
| 接口路径 | `/api/v1/recommendations` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 可以。第一阶段推荐结果页先 mock 当前高校内 3-5 条专业建议 |

#### 接口含义调整

`/api/v1/recommendations` 可以保留，但含义必须从“推荐多个高校”调整为：

> 在当前 `X-Tenant` 对应高校内，根据学生画像、分数、省份、科类、兴趣、意向专业等信息，返回本校专业推荐、学院介绍、报考建议和风险提示。

后端返回结果不得包含其他高校。

#### 前端传入参数

当前前端封装支持分页：

```ts
interface GetRecommendationsQuery {
  page?: number
  page_size?: number
}
```

请求示例：

```txt
GET /api/v1/recommendations?page=1&page_size=20
```

#### 后端返回字段

为兼容已有前端字段，第一阶段可以保留 `RecommendationItem`，但字段语义调整如下：

```ts
interface RecommendationItem {
  id: string
  college_id?: string
  college_name: string
  major_name: string
  province: string
  city: string
  level: string
  match_score: number
  min_score?: number
  min_rank?: number
  subjects?: string
  reasons: string[]
  risk_level?: "safe" | "match" | "reach"
}
```

字段说明：

| 字段 | 新语义 |
|---|---|
| college_id | 当前高校 ID 或租户高校 ID |
| college_name | 当前高校名称，例如华南师范大学 |
| major_name | 当前高校内推荐专业 |
| province | 当前高校所在省份 |
| city | 当前高校所在城市 |
| level | 专业或招生层次，例如本科 |
| match_score | 学生画像与本校专业的匹配度 |
| min_score | 当前高校该专业往年最低分，可选 |
| min_rank | 当前高校该专业往年最低位次，可选 |
| subjects | 选科要求 |
| reasons | 推荐理由 / 报考建议 |
| risk_level | 报考风险：`reach` 偏冲、`match` 较匹配、`safe` 较稳 |

注意：`risk_level` 只表示本校不同专业之间的报考风险，不表示多所高校之间的冲稳保。

#### 完整返回示例

```ts
interface PaginationData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

type GetRecommendationsResponse = ApiResponse<PaginationData<RecommendationItem>>
```

```json
{
  "data": {
    "items": [
      {
        "id": "rec_001",
        "college_id": "tenant_scnu",
        "college_name": "华南师范大学",
        "major_name": "人工智能",
        "province": "广东",
        "city": "广州",
        "level": "本科",
        "match_score": 92,
        "min_score": 579,
        "min_rank": 38000,
        "subjects": "物理+不限",
        "reasons": [
          "该专业与学生的计算机和人工智能兴趣匹配度较高",
          "学生当前分数与本校该专业近年录取区间较接近",
          "适合关注技术成长、就业前景和城市发展的学生"
        ],
        "risk_level": "match"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "error": null
}
```

---

### 7.2 提交推荐反馈

| 项 | 内容 |
|---|---|
| 接口名称 | 提交本校专业推荐反馈 |
| 请求方法 | `POST` |
| 接口路径 | `/api/v1/recommendations/feedback` |
| 第一阶段状态 | 已有契约 + 已有前端封装；后端实现待确认 |
| 是否可 mock | 第一阶段可暂不做真实提交 |

#### 前端传入参数

```ts
interface SubmitRecommendationFeedbackRequest {
  recommendation_id: string
  rating: number
  comment?: string
}
```

#### 后端返回字段

```ts
interface SubmitRecommendationFeedbackData {
  success: boolean
}
```

---

## 8. 本校专业对比 / 意向专业分析 API

### 8.1 获取本校专业对比 / 意向专业分析

| 项 | 内容 |
|---|---|
| 接口名称 | 获取本校专业对比 / 意向专业分析 |
| 请求方法 | `GET` |
| 接口路径 | `/api/v1/compare/recommendations` |
| 第一阶段状态 | README 和前端封装已有；CONVENTIONS 需确认是否补充或重命名 |
| 是否可 mock | 可以。第一阶段对比页先 mock 当前高校内多个专业对比 |

#### 接口含义调整

`/api/v1/compare/recommendations` 如果保留，只能用于：

> 当前 `X-Tenant` 对应高校内多个专业、学院或培养方向之间的对比与意向分析。

不得用于多个高校之间的对比，也不得返回其他高校。

如果后端认为路径命名 `compare/recommendations` 容易误导，第二阶段可考虑更名为：

```txt
/api/v1/majors/compare
```

但第一阶段不强行改动已有前端封装路径。

#### 前端传入参数

当前前端封装支持传入画像快照：

```ts
interface GetCompareRecommendationsQuery {
  profile_snapshot?: string
}
```

请求示例：

```txt
GET /api/v1/compare/recommendations?profile_snapshot=%7B...%7D
```

#### 后端返回字段

为兼容已有前端字段，第一阶段可以保留以下结构，但字段语义调整为“当前高校内学院 / 专业对比”。

```ts
interface CompareMajorItem {
  college_name: string
  major_name: string
  level: string
  province: string
  city: string
  min_rank: number
  min_score: number
  subjects: string
  source_url: string
}

interface CompareRecommendationItem {
  tenant_slug: string
  tenant_name: string
  majors: CompareMajorItem[]
  match_score: number
}

interface CompareRecommendationsData {
  recommendations: CompareRecommendationItem[]
  profile_snapshot: ProfileSnapshot
  tenants_compared: number
}
```

字段说明：

| 字段 | 新语义 |
|---|---|
| tenant_slug | 当前高校租户 slug，例如 `scnu` |
| tenant_name | 当前高校名称，例如华南师范大学 |
| majors | 当前高校内用于对比的专业列表 |
| college_name | 当前高校下属学院名称，例如计算机学院、软件学院 |
| major_name | 专业名称 |
| match_score | 学生画像与该专业组或专业方向的匹配度 |
| tenants_compared | 第一阶段应固定为 `1`，表示只分析当前租户高校 |

#### 完整返回示例

```ts
type GetCompareRecommendationsResponse = ApiResponse<CompareRecommendationsData>
```

```json
{
  "data": {
    "recommendations": [
      {
        "tenant_slug": "scnu",
        "tenant_name": "华南师范大学",
        "match_score": 92,
        "majors": [
          {
            "college_name": "计算机学院",
            "major_name": "人工智能",
            "level": "本科",
            "province": "广东",
            "city": "广州",
            "min_rank": 38000,
            "min_score": 579,
            "subjects": "物理+不限",
            "source_url": "https://example.com/admission/scnu-ai"
          },
          {
            "college_name": "软件学院",
            "major_name": "软件工程",
            "level": "本科",
            "province": "广东",
            "city": "广州",
            "min_rank": 39500,
            "min_score": 576,
            "subjects": "物理+不限",
            "source_url": "https://example.com/admission/scnu-se"
          },
          {
            "college_name": "计算机学院",
            "major_name": "数据科学与大数据技术",
            "level": "本科",
            "province": "广东",
            "city": "广州",
            "min_rank": 41000,
            "min_score": 573,
            "subjects": "物理+不限",
            "source_url": "https://example.com/admission/scnu-data"
          }
        ]
      }
    ],
    "profile_snapshot": {
      "riasec": {
        "I": 8,
        "E": 6
      },
      "values": ["技术成长", "就业前景"],
      "confidence": 0.76,
      "completeness": "L2"
    },
    "tenants_compared": 1
  },
  "error": null
}
```

---

## 9. 第一阶段 mock 数据结构

第一阶段后端未就绪时，C 端可以先 mock 以下数据。

所有 mock 数据必须围绕当前高校，例如华南师范大学，不得出现多个不同高校。

### 9.1 演示学生信息

```ts
const mockStudentInfo: StudentBasicInfo = {
  province: "广东",
  subject_type: "物理类",
  score: 585,
  intent_majors: ["计算机", "人工智能"]
}
```

### 9.2 mock 画像

```ts
const mockProfile: ProfileSnapshot = {
  riasec: {
    R: 4,
    I: 8,
    A: 5,
    S: 4,
    E: 6,
    C: 3
  },
  values: ["技术成长", "就业前景", "城市发展"],
  confidence: 0.76,
  completeness: "L2"
}
```

### 9.3 mock 聊天回复

```ts
const mockAssistantMessage: WsAssistantMessage = {
  type: "message",
  content: "根据你的分数和兴趣，可以重点了解本校的人工智能、软件工程、数据科学与大数据技术等专业方向。我可以继续帮你分析这些专业的培养方向、录取风险和就业去向。",
  stage: "explore"
}
```

### 9.4 mock 本校专业推荐结果

```ts
const mockRecommendations: RecommendationItem[] = [
  {
    id: "rec_001",
    college_id: "tenant_scnu",
    college_name: "华南师范大学",
    major_name: "人工智能",
    province: "广东",
    city: "广州",
    level: "本科",
    match_score: 92,
    min_score: 579,
    min_rank: 38000,
    subjects: "物理+不限",
    reasons: ["兴趣匹配", "分数接近", "就业方向较好"],
    risk_level: "match"
  },
  {
    id: "rec_002",
    college_id: "tenant_scnu",
    college_name: "华南师范大学",
    major_name: "软件工程",
    province: "广东",
    city: "广州",
    level: "本科",
    match_score: 88,
    min_score: 576,
    min_rank: 39500,
    subjects: "物理+不限",
    reasons: ["编程方向匹配", "实践课程较多", "就业面较广"],
    risk_level: "match"
  },
  {
    id: "rec_003",
    college_id: "tenant_scnu",
    college_name: "华南师范大学",
    major_name: "数据科学与大数据技术",
    province: "广东",
    city: "广州",
    level: "本科",
    match_score: 84,
    min_score: 573,
    min_rank: 41000,
    subjects: "物理+不限",
    reasons: ["与人工智能方向关联度高", "适合数学和数据分析兴趣", "可作为本校内的稳妥选择"],
    risk_level: "safe"
  }
]
```

### 9.5 mock 本校专业对比 / 意向专业分析

```ts
const mockCompareRecommendationsData: CompareRecommendationsData = {
  recommendations: [
    {
      tenant_slug: "scnu",
      tenant_name: "华南师范大学",
      match_score: 92,
      majors: [
        {
          college_name: "计算机学院",
          major_name: "人工智能",
          level: "本科",
          province: "广东",
          city: "广州",
          min_rank: 38000,
          min_score: 579,
          subjects: "物理+不限",
          source_url: "https://example.com/admission/scnu-ai"
        },
        {
          college_name: "软件学院",
          major_name: "软件工程",
          level: "本科",
          province: "广东",
          city: "广州",
          min_rank: 39500,
          min_score: 576,
          subjects: "物理+不限",
          source_url: "https://example.com/admission/scnu-se"
        }
      ]
    }
  ],
  profile_snapshot: mockProfile,
  tenants_compared: 1
}
```

---

## 10. 第一阶段暂不做的功能

以下功能建议放到第二阶段：

1. 真实登录注册完整闭环；
2. 多轮历史会话列表；
3. 推荐结果复杂筛选和排序；
4. 收藏专业 / 收藏报考方案；
5. 完整志愿表生成；
6. 支付、预约咨询、人工老师介入；
7. 复杂测评问卷；
8. 推荐算法解释的复杂可视化；
9. 微信小程序正式发布相关能力；
10. 多租户跨学校真实生产数据联调；
11. 跨院校对比；
12. 推荐其他高校；
13. 多学校冲稳保方案。

---

## 11. 后端需要确认的问题清单

1. `POST /api/v1/chat/session` 是否已经真实实现？
2. 创建会话返回是否严格为 `{ data: { session_id, guest }, error: null }`？
3. WebSocket 是否最终使用 `/api/v1/chat/session/{id}?tenant=scnu`？
4. WebSocket 是否需要 token 鉴权？如果需要，token 放 query 还是通过握手 header？
5. 聊天 Agent 是否已经加入单校约束，确保只回答当前 `X-Tenant` 对应高校内容？
6. `GET /api/v1/profiles` 返回的是当前学生画像，还是画像列表？
7. `/profiles` 是否补充 `province`、`subject_type`、`score`、`intent_majors`、`focus_points` 等招生线索字段？
8. `GET /api/v1/recommendations` 是否按当前租户高校内专业进行推荐，而不是返回其他高校？
9. 推荐结果中的 `college_name` 是否固定为当前租户高校名称？
10. `/compare/recommendations` 是否保留作为本校专业对比接口，还是后续更名为 `/api/v1/majors/compare`？
11. `CompareRecommendationsData.tenants_compared` 在单校模式下是否固定为 `1`？
12. 第一阶段 C 端使用单校 mock 数据演示是否可以先合并？
13. 后端返回字段命名是否统一使用 snake_case，例如 `session_id`、`match_score`、`min_score`？

---

## 12. 当前发现的前端契约风险

### 12.1 `chat.ts` 读取创建会话返回值的方式与统一返回格式不一致

当前统一返回格式是：

```ts
{
  data: T | null
  error: ApiError | null
}
```

因此创建会话后应读取：

```ts
res.data?.session_id
```

而不是：

```ts
res?.session_id
```

后续开发聊天页 mock / 真接口兼容时需要修正。

### 12.2 `websocket.ts` 当前偏 H5 写法

当前 WebSocket 使用了：

- 原生 `WebSocket`
- `location.host`
- `window.setInterval`

如果后续要发布微信小程序，需要改为 `uni.connectSocket`、`uni.sendSocketMessage`、`uni.closeSocket` 等跨端写法。

第一阶段如果只做 H5 演示，可以暂时不改；如果答辩需要真机微信小程序预览，需要提前处理。

### 12.3 现有页面和命名存在“跨院校对比”历史遗留

当前已有页面路径中存在 `pages/compare/index`，部分旧文案可能仍然表达为“跨院校对比”。

在新定位下：

- 页面路径可以暂时保留；
- UI 文案必须调整为“本校专业对比”或“意向专业分析”；
- 前端 mock 数据不得出现其他高校；
- 后端接口不得返回其他高校。
