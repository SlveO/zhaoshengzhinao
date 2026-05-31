# C 端前端封版与后端接口对接说明

## 一、C 端小程序当前产品定位

本项目 C 端小程序是部署在“华南师范大学”公众号里的**单高校招生智能咨询小程序**。

学生进入小程序后，主要围绕华南师范大学进行咨询和查看信息，包括：

- 华南师范大学招生政策
- 华南师范大学专业介绍
- 华南师范大学录取参考
- 华南师范大学报考建议
- 华南师范大学校园生活
- 华南师范大学招生联系方式
- 华南师范大学招生咨询群

本项目 C 端不是多院校对比平台，不提供其他高校推荐，不做跨院校对比，也不引导学生查看其他高校。

当前 C 端核心价值是：

1. 帮助高校提高招生咨询效率；
2. 通过 AI 咨询沉淀学生咨询档案；
3. 采集学生省份、科类、分数、意向专业、关注点等信息；
4. 为后续 B 端招生数据分析和线索转化提供数据基础；
5. 通过 `session_id` 恢复用户数据，避免学生下次进入小程序时从零开始。

---

## 二、当前前端页面清单

| 模块 | 文件路径 | 页面定位 |
|---|---|---|
| AI 咨询首页 | `pages/chat/index.vue` | 学生进入后的核心 AI 招生咨询入口 |
| 本校专业推荐 / 报考建议 | `pages/recommendations/index.vue` | 展示华南师范大学校内专业推荐和报考参考 |
| 专业分析详情页 | `pages/compare/index.vue` | 展示华南师范大学本校专业分析详情 |
| 学校信息页 | `pages/school/index.vue` | 展示学校概况、学院专业、招生政策等入口 |
| 我的咨询档案 | `pages/profile/index.vue` | 展示当前学生咨询档案和演示档案 |
| session 工具 | `utils/session.ts` | 本地保存、读取、清除 `session_id` |

当前底部 tabBar 为：

1. AI咨询
2. 报考建议
3. 学校信息
4. 我的

其中 `pages/compare/index.vue` 不在底部 tabBar 中，只作为“专业分析详情页”，从报考建议页进入。

---

## 三、当前前端状态

当前 C 端前端 MVP 已经基本完成，页面使用 mock 数据进行演示。

当前状态说明：

1. 前端页面已经具备完整展示效果；
2. 当前聊天回复仍为前端 mock 回复；
3. 当前报考建议页仍使用 mock 专业推荐数据；
4. 当前专业分析详情页仍使用页面内 mock 分析内容；
5. 当前咨询档案页仍使用 mock 学生档案数据；
6. 前端已新增 `utils/session.ts`，用于本地保存和读取 `session_id`；
7. 前端 API 调用层暂不强制实现；
8. 后续等后端接口完成后，再新增前端 API 调用层，并逐步替换 mock 数据。

当前本地 session key 为：

```txt
scnu_consult_session_id
```

当前前端会话逻辑：

```txt
学生进入小程序
↓
前端读取本地 session_id
↓
如果没有 session_id，先生成 mock_session_时间戳
↓
保存到本地
↓
后续页面通过 session_id 识别当前咨询会话
```

后续真实后端接入后，流程应改为：

```txt
学生进入小程序
↓
前端读取本地 session_id
↓
调用 POST /api/v1/miniapp/enter
↓
后端创建或恢复咨询会话
↓
返回真实 session_id、历史聊天记录、咨询档案摘要
↓
前端保存 session_id 并渲染恢复后的数据
```

---

## 四、后端第一阶段需要实现的 5 个接口

第一阶段后端 MVP 建议先实现以下 5 个接口：

| 序号 | 接口 | 作用 |
|---|---|---|
| 1 | `POST /api/v1/miniapp/enter` | 创建或恢复小程序咨询会话 |
| 2 | `POST /api/v1/chat/messages` | 发送用户消息并返回 AI 回复 |
| 3 | `GET /api/v1/student/profile` | 根据 `session_id` 获取学生咨询档案 |
| 4 | `POST /api/v1/recommendations` | 根据咨询档案生成华南师范大学本校专业推荐 |
| 5 | `GET /api/v1/majors/analysis` | 根据 `session_id` 和专业名获取本校专业分析详情 |

---

## 五、统一接口约定

### 1. API 前缀

```txt
/api/v1
```

### 2. 当前租户

```txt
tenant_slug = scnu
tenant_name = 华南师范大学
```

### 3. 请求头

所有 C 端接口建议统一携带：

```http
X-Tenant: scnu
Content-Type: application/json
```

GET 请求可以不带 `Content-Type`，但仍建议携带：

```http
X-Tenant: scnu
```

### 4. 统一返回格式

成功：

```json
{
  "data": {},
  "error": null
}
```

失败：

```json
{
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误说明"
  }
}
```

### 5. session_id 约定

`session_id` 是 C 端第一阶段识别用户咨询会话的核心字段。

后端需要保证以下数据都绑定 `session_id`：

- 聊天记录
- 学生咨询档案
- 报考建议
- 专业分析结果
- 用户意向专业
- 用户关注点
- 用户省份、科类、分数等信息

---

## 六、接口一：创建或恢复小程序咨询会话

### 接口名称

创建或恢复 C 端咨询会话

### 请求方法

```http
POST
```

### 接口路径

```txt
/api/v1/miniapp/enter
```

### 作用

学生进入小程序时调用。

如果前端本地没有 `session_id`，后端创建新会话并返回新的 `session_id`。

如果前端本地已有 `session_id`，后端根据该 `session_id` 恢复历史聊天记录、咨询档案摘要等数据。

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | `string \| null` | 否 | 前端本地已有的会话 ID，首次进入可传 `null` |
| `tenant_slug` | `string` | 是 | 当前租户，第一阶段固定为 `scnu` |
| `scene` | `string` | 否 | 进入场景，建议传 `miniapp_enter` |

### 请求 JSON 示例

首次进入：

```json
{
  "session_id": null,
  "tenant_slug": "scnu",
  "scene": "miniapp_enter"
}
```

再次进入：

```json
{
  "session_id": "sess_20260524_001",
  "tenant_slug": "scnu",
  "scene": "miniapp_enter"
}
```

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 后端生成或确认的会话 ID |
| `tenant_slug` | `string` | 当前租户标识 |
| `tenant_name` | `string` | 当前高校名称 |
| `is_new_session` | `boolean` | 是否为新会话 |
| `has_profile` | `boolean` | 是否已有学生咨询档案 |
| `chat_history` | `array` | 历史聊天记录 |
| `profile_summary` | `object \| null` | 学生咨询档案摘要 |

### 返回 JSON 示例

```json
{
  "data": {
    "session_id": "sess_20260524_001",
    "tenant_slug": "scnu",
    "tenant_name": "华南师范大学",
    "is_new_session": false,
    "has_profile": true,
    "chat_history": [
      {
        "message_id": "msg_001",
        "role": "assistant",
        "content": "你好，我是华南师范大学招生咨询助手。你可以直接问我招生政策、专业介绍、录取参考、校园生活等问题。",
        "created_at": "2026-05-24T10:00:00+08:00"
      },
      {
        "message_id": "msg_002",
        "role": "user",
        "content": "广东物理类 585 分适合报华师哪些专业？",
        "created_at": "2026-05-24T10:01:00+08:00"
      }
    ],
    "profile_summary": {
      "province": "广东",
      "subject_type": "物理类",
      "score": 585,
      "intent_majors": ["计算机", "人工智能"],
      "focus_points": ["专业实力", "就业方向", "录取参考"]
    }
  },
  "error": null
}
```

---

## 七、接口二：发送聊天消息并获取 AI 回复

### 接口名称

发送聊天消息

### 请求方法

```http
POST
```

### 接口路径

```txt
/api/v1/chat/messages
```

### 作用

用户在 AI 咨询页发送问题后调用。

后端需要：

1. 保存用户消息；
2. 基于华南师范大学招生知识生成 AI 回复；
3. 从对话中抽取学生信息；
4. 更新学生咨询档案；
5. 返回 AI 回复和档案摘要。

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | `string` | 是 | 当前咨询会话 ID |
| `tenant_slug` | `string` | 是 | 当前租户，固定为 `scnu` |
| `message.role` | `string` | 是 | 消息角色，前端发送固定为 `user` |
| `message.content` | `string` | 是 | 用户输入内容 |

### 请求 JSON 示例

```json
{
  "session_id": "sess_20260524_001",
  "tenant_slug": "scnu",
  "message": {
    "role": "user",
    "content": "广东物理类 585 分适合报华师哪些专业？"
  }
}
```

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 当前咨询会话 ID |
| `assistant_message` | `object` | AI 回复消息 |
| `profile_updated` | `boolean` | 本轮对话是否更新了咨询档案 |
| `profile_summary` | `object \| null` | 更新后的咨询档案摘要 |

### 返回 JSON 示例

```json
{
  "data": {
    "session_id": "sess_20260524_001",
    "assistant_message": {
      "message_id": "msg_003",
      "role": "assistant",
      "content": "以广东物理类 585 分为例，可以重点关注华南师范大学校内与计算机、人工智能、软件工程、数据科学相关的专业方向。具体还要结合当年招生计划、专业组、最低位次和你的专业偏好综合判断。",
      "created_at": "2026-05-24T10:02:00+08:00"
    },
    "profile_updated": true,
    "profile_summary": {
      "province": "广东",
      "subject_type": "物理类",
      "score": 585,
      "intent_majors": ["计算机", "人工智能"],
      "focus_points": ["专业实力", "就业方向", "录取参考"]
    }
  },
  "error": null
}
```

---

## 八、接口三：获取学生咨询档案

### 接口名称

获取学生咨询档案

### 请求方法

```http
GET
```

### 接口路径

```txt
/api/v1/student/profile
```

### 作用

用于“我的咨询档案”页，也可用于报考建议页生成推荐前读取学生档案。

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | `string` | 是 | 当前咨询会话 ID |

### 请求示例

```txt
/api/v1/student/profile?session_id=sess_20260524_001
```

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 当前咨询会话 ID |
| `has_profile` | `boolean` | 是否已有咨询档案 |
| `profile` | `object \| null` | 学生咨询档案 |

### 返回 JSON 示例：已有档案

```json
{
  "data": {
    "session_id": "sess_20260524_001",
    "has_profile": true,
    "profile": {
      "province": "广东",
      "subject_type": "物理类",
      "score": 585,
      "intent_majors": ["计算机", "人工智能"],
      "focus_points": ["专业实力", "就业方向", "录取参考"],
      "consult_stage": "profile_ready",
      "updated_at": "2026-05-24T10:05:00+08:00"
    }
  },
  "error": null
}
```

### 返回 JSON 示例：暂无档案

```json
{
  "data": {
    "session_id": "sess_20260524_001",
    "has_profile": false,
    "profile": null
  },
  "error": null
}
```

---

## 九、接口四：获取本校专业推荐 / 报考建议

### 接口名称

生成本校专业推荐

### 请求方法

```http
POST
```

### 接口路径

```txt
/api/v1/recommendations
```

### 作用

根据当前学生咨询档案，生成华南师范大学校内专业推荐和报考建议。

该接口只能返回华南师范大学本校专业，不能返回其他高校。

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | `string` | 是 | 当前咨询会话 ID |
| `tenant_slug` | `string` | 是 | 当前租户，固定为 `scnu` |
| `profile_snapshot` | `object` | 否 | 前端可传当前档案快照，后端也可按 `session_id` 自行读取 |

### 请求 JSON 示例

```json
{
  "session_id": "sess_20260524_001",
  "tenant_slug": "scnu",
  "profile_snapshot": {
    "province": "广东",
    "subject_type": "物理类",
    "score": 585,
    "intent_majors": ["计算机", "人工智能"],
    "focus_points": ["专业实力", "就业方向", "录取参考"]
  }
}
```

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 当前咨询会话 ID |
| `tenant_slug` | `string` | 当前租户 |
| `tenant_name` | `string` | 当前高校名称 |
| `items` | `array` | 本校专业推荐列表 |
| `disclaimer` | `string` | 报考参考免责声明 |

### 推荐项字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `string` | 推荐项 ID |
| `college_id` | `string` | 高校 ID，第一阶段可为 `tenant_scnu` |
| `college_name` | `string` | 固定为 `华南师范大学` |
| `major_name` | `string` | 专业名称 |
| `province` | `string` | 省份 |
| `city` | `string` | 城市 |
| `level` | `string` | 层次，例如 `本科` |
| `match_score` | `number` | 匹配度 |
| `risk_level` | `string` | 风险等级，可为 `reach`、`match`、`safe` |
| `risk_label` | `string` | 中文风险标签 |
| `min_score` | `number` | 参考最低分 |
| `min_rank` | `number` | 参考最低位次 |
| `subjects` | `string` | 选科要求 |
| `reasons` | `string[]` | 推荐理由 |

### 返回 JSON 示例

```json
{
  "data": {
    "session_id": "sess_20260524_001",
    "tenant_slug": "scnu",
    "tenant_name": "华南师范大学",
    "items": [
      {
        "id": "rec_001",
        "college_id": "tenant_scnu",
        "college_name": "华南师范大学",
        "major_name": "人工智能",
        "province": "广东",
        "city": "广州",
        "level": "本科",
        "match_score": 91,
        "risk_level": "reach",
        "risk_label": "可冲",
        "min_score": 589,
        "min_rank": 34500,
        "subjects": "物理+不限",
        "reasons": [
          "专业方向与智能系统、算法应用和数据能力高度相关",
          "适合对编程、数学建模和人工智能应用有持续兴趣的学生",
          "该方向竞争相对更强，建议结合当年专业组计划谨慎填报"
        ]
      },
      {
        "id": "rec_002",
        "college_id": "tenant_scnu",
        "college_name": "华南师范大学",
        "major_name": "软件工程",
        "province": "广东",
        "city": "广州",
        "level": "本科",
        "match_score": 88,
        "risk_level": "match",
        "risk_label": "较匹配",
        "min_score": 582,
        "min_rank": 38200,
        "subjects": "物理+不限",
        "reasons": [
          "更偏工程实践、系统开发和项目落地，与计算机兴趣匹配度高",
          "培养方向与软件开发、平台建设和应用工程相关",
          "分数条件与演示档案较匹配，可作为重点关注方向"
        ]
      },
      {
        "id": "rec_003",
        "college_id": "tenant_scnu",
        "college_name": "华南师范大学",
        "major_name": "数据科学与大数据技术",
        "province": "广东",
        "city": "广州",
        "level": "本科",
        "match_score": 84,
        "risk_level": "safe",
        "risk_label": "较稳妥",
        "min_score": 575,
        "min_rank": 42100,
        "subjects": "物理+不限",
        "reasons": [
          "面向数据分析、数据平台和智能决策等应用场景",
          "适合同时关注计算机技术、数据能力和行业应用的学生",
          "整体风险相对更稳妥，可作为本校专业组合中的补充选择"
        ]
      }
    ],
    "disclaimer": "以下建议为华南师范大学校内专业报考参考，不代表录取承诺。"
  },
  "error": null
}
```

---

## 十、接口五：获取本校专业分析详情

### 接口名称

获取专业分析详情

### 请求方法

```http
GET
```

### 接口路径

```txt
/api/v1/majors/analysis
```

### 作用

用于 `pages/compare/index.vue` 专业分析详情页。

根据 `session_id` 和专业名称，返回该学生对该专业的匹配度分析、风险说明和后续咨询建议。

该接口只能分析华南师范大学本校专业，不能做跨院校对比。

### 请求参数

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | `string` | 是 | 当前咨询会话 ID |
| `major` | `string` | 是 | 专业名称，例如 `人工智能` |

### 请求示例

```txt
/api/v1/majors/analysis?session_id=sess_20260524_001&major=人工智能
```

### 返回字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `session_id` | `string` | 当前咨询会话 ID |
| `tenant_slug` | `string` | 当前租户 |
| `tenant_name` | `string` | 当前高校名称 |
| `major` | `object` | 专业核心信息 |
| `analysis` | `object` | 专业分析内容 |

### 返回 JSON 示例

```json
{
  "data": {
    "session_id": "sess_20260524_001",
    "tenant_slug": "scnu",
    "tenant_name": "华南师范大学",
    "major": {
      "name": "人工智能",
      "college_name": "华南师范大学",
      "match_score": 92,
      "risk_label": "可冲",
      "min_score": 589,
      "min_rank": "34,000",
      "subjects": "物理+不限"
    },
    "analysis": {
      "fit_reasons": [
        "你的意向方向包含计算机与人工智能，和该专业培养方向高度相关",
        "该专业适合对算法、编程、智能系统和数据应用感兴趣的学生",
        "你的演示分数接近该专业参考区间，可以作为重点关注方向"
      ],
      "risk_desc": "该专业热度较高，竞争相对更强。当前演示分数与参考最低分较接近，建议结合当年招生计划、专业组设置和最低位次综合判断。",
      "focus_points": ["算法基础", "编程能力", "智能系统", "专业组计划"],
      "next_consult_suggestion": "你可以继续向 AI 咨询该专业的课程设置、培养方向、近年录取参考、就业去向和所在学院情况。"
    }
  },
  "error": null
}
```

---

## 十一、后端必须遵守的产品约束

### 1. 当前 tenant_slug 为 scnu

第一阶段当前租户固定为：

```txt
tenant_slug = scnu
tenant_name = 华南师范大学
```

后端需要根据 `X-Tenant: scnu` 或请求体中的 `tenant_slug: scnu` 限定数据范围。

### 2. 只能回答华南师范大学相关内容

AI 咨询回复必须限定在华南师范大学范围内。

允许回答：

- 华南师范大学招生政策
- 华南师范大学专业介绍
- 华南师范大学报考建议
- 华南师范大学录取参考
- 华南师范大学校园生活
- 华南师范大学招生联系方式
- 华南师范大学招生咨询群

不应引导学生查看其他高校。

### 3. 不能推荐其他高校

所有推荐结果中的 `college_name` 必须为：

```txt
华南师范大学
```

所有推荐结果中的 `college_id` 第一阶段建议为：

```txt
tenant_scnu
```

后端不能返回其他高校名称。

### 4. 不能做跨院校对比

`pages/compare/index.vue` 当前是“专业分析详情页”，不是跨院校对比页。

后端不能返回：

- 跨院校对比内容
- 多高校对比内容
- 其他学校推荐
- 对比学校列表

允许返回：

- 华南师范大学校内专业分析
- 本校专业匹配度分析
- 本校专业风险说明
- 本校专业建议关注点

### 5. 所有聊天记录、咨询档案、报考建议都要绑定 session_id

后端数据库中以下数据都必须绑定 `session_id`：

- 咨询会话
- 聊天消息
- 学生咨询档案
- 专业推荐结果
- 专业分析结果
- 学生关注点
- 学生意向专业
- 学生省份、科类、分数

建议后端数据表至少包含：

- `consult_sessions`
- `chat_messages`
- `student_profiles`
- `recommendation_results`
- `major_analysis_results`

### 6. 用户下次进入小程序时要能通过 session_id 恢复数据

用户再次进入小程序时，前端会读取本地保存的 `session_id`，并调用：

```txt
POST /api/v1/miniapp/enter
```

后端需要根据 `session_id` 返回：

- 是否为新会话
- 历史聊天记录
- 是否已有咨询档案
- 咨询档案摘要
- 必要时返回推荐结果摘要

目标是避免用户每次进入小程序都从零开始。

---

## 十二、后续联调阶段再做的内容

以下内容不属于当前前端封版阶段，建议放到后续联调或第二阶段再做。

### 1. 新增前端 API 调用层

当前不新增 `src/api/consult.ts`。

后续接口确定并可用后，再统一新增前端 API 调用层，例如：

- 创建或恢复会话
- 发送聊天消息
- 获取咨询档案
- 获取本校专业推荐
- 获取专业分析详情

### 2. 将 mock 数据替换为真实接口

当前前端仍使用 mock 数据演示。

后续替换顺序建议：

1. 先接入 `/api/v1/miniapp/enter`，打通 `session_id`；
2. 再接入 `/api/v1/chat/messages`，替换聊天 mock 回复；
3. 再接入 `/api/v1/student/profile`，替换咨询档案 mock；
4. 再接入 `/api/v1/recommendations`，替换报考建议 mock；
5. 最后接入 `/api/v1/majors/analysis`，替换专业分析 mock。

### 3. 微信 openid 绑定

第一阶段不做强制登录页。

第二阶段可以接入微信 openid，将：

- `openid`
- `unionid`
- `session_id`

进行绑定。

作用：

- 更稳定识别同一学生；
- 支持清缓存后的会话恢复；
- 支持后续招生线索追踪。

### 4. 手机号留资

第一阶段不做强制手机号登录。

第二阶段可以在合适场景引导学生自愿留资，例如：

- 想接收招生提醒；
- 想加入招生咨询群；
- 想获取更详细报考建议；
- 想让招生老师后续联系。

### 5. 后台数据分析

第二阶段 B 端可以基于 C 端数据做招生分析，包括：

- 咨询人数
- 热门专业
- 高频问题
- 省份分布
- 分数段分布
- 科类分布
- 意向专业分布
- 学生关注点分布
- 高意向学生线索
- 咨询转化情况

---

## 十三、当前交付结论

当前 C 端小程序前端 MVP 已基本完成，可以进入“接口定义交付 / 后端开发准备”阶段。

当前前端交付重点是：

1. 页面已完成第一阶段展示；
2. mock 数据可支撑国创赛演示；
3. 已明确单高校产品定位；
4. 已预留 `session_id` 会话恢复机制；
5. 已明确后端第一阶段需要实现的 5 个接口；
6. 后续不需要新增传统登录页，也不需要强制手机号登录；
7. 后端优先实现会话恢复、聊天消息、咨询档案、本校专业推荐和专业分析详情即可。
