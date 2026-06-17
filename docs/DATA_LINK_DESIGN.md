# 数据链路设计文档

## 1. 数据链路目标

本数据链路面向高校招生咨询场景，把学生与 AI 助手之间的自然语言问答转化为可保存、可追踪、可统计、可展示的结构化数据。当前版本先用规则提取和本地 JSON mock 存储跑通闭环，后续可以平滑替换为 DeepSeek JSON 抽取和 PostgreSQL / Redis 等真实存储。

核心目标：

- 记录每轮学生问题和 AI 回复，形成完整 `ChatSession`。
- 从对话中提取省份、科类、分数、位次、意向专业、关注点和联系意向。
- 多轮合并学生信息，生成稳定的 `StudentProfile`。
- 计算 `intentScore` 和 `intentLevel`，辅助招生办识别高意向线索。
- 聚合生成 `ConsultationReport`，为后台看板提供热门专业、关注点、省份和分数段统计。

## 2. 整体流程

```text
学生输入咨询问题
  -> AI 助手生成回复
  -> processConsultationTurn 记录 user / assistant 消息
  -> extractStudentInfo 从学生问题中提取结构化字段
  -> 可补充读取 AI 回复中的专业和关注点
  -> updateStudentProfile 合并多轮学生画像
  -> calculateIntentScore / generateStudentTags 生成意向分和标签
  -> generateConsultationReport 生成租户维度统计
  -> JsonDataLinkStore 写入 data/mock/*.json
```

当前代码位置：

- `backend/services/data_link.py`：核心类型、字段提取、画像更新、评分、标签、报告、总流程。
- `backend/services/data_link_store.py`：本地 JSON 存储适配器。
- `scripts/data_link_demo.py`：三名学生多轮咨询 demo。

## 3. 对话记录 JSON 结构

`ChatMessage`：

```json
{
  "id": "msg_xxx",
  "tenantId": "tenant_scnu",
  "studentId": "stu_demo_001",
  "sessionId": "session_demo_001",
  "role": "user",
  "content": "我是广东物理类考生，585分，想问人工智能专业稳不稳？",
  "createdAt": "2026-06-17T00:00:00+00:00"
}
```

`ChatSession`：

```json
{
  "sessionId": "session_demo_001",
  "tenantId": "tenant_scnu",
  "studentId": "stu_demo_001",
  "messages": [],
  "startedAt": "2026-06-17T00:00:00+00:00",
  "updatedAt": "2026-06-17T00:01:00+00:00"
}
```

## 4. 学生画像 JSON 结构

`StudentProfile`：

```json
{
  "studentId": "stu_demo_001",
  "tenantId": "tenant_scnu",
  "province": "广东",
  "subjectType": "物理类",
  "score": 585,
  "rank": 32000,
  "interestedMajors": ["人工智能", "软件工程"],
  "concerns": ["录取概率", "专业分数线", "招生群"],
  "contactIntent": true,
  "tags": ["广东考生", "物理类", "585分", "高意向", "关注人工智能"],
  "intentScore": 100,
  "intentLevel": "high",
  "consultationCount": 2,
  "firstConsultedAt": "2026-06-17T00:00:00+00:00",
  "lastConsultedAt": "2026-06-17T00:01:00+00:00"
}
```

多轮合并规则：

- 新一轮没有提到的单值字段不会清空旧值。
- 新一轮明确提到的 `province`、`subjectType`、`score`、`rank` 可以覆盖旧值。
- `interestedMajors`、`concerns`、`tags` 会追加并去重。
- 每处理一轮咨询，`consultationCount` 加 1，`lastConsultedAt` 更新。
- 首次咨询时设置 `firstConsultedAt`。

## 5. 字段提取规则

当前版本使用规则提取，入口为：

```python
extractStudentInfo(text: str) -> ExtractedStudentInfo
```

支持字段：

- `province`：识别广东、湖南、广西、福建、江西、湖北、河南、河北、山东、山西、江苏、浙江、安徽、四川、重庆、贵州、云南、陕西、甘肃、辽宁、吉林、黑龙江、北京、天津、上海、海南、内蒙古、新疆、西藏、青海、宁夏。
- `subjectType`：识别物理类、历史类、理科、文科，并支持“选物理”“选历史”“理科生”“文科生”等表达。
- `score`：识别“585分”“高考585”“分数585”“考了585”等三位分数，避免把年份当分数。
- `rank`：识别“32000名”“位次32000”“排名32000”“排位32000”。
- `interestedMajors`：识别人工智能、软件工程、计算机科学与技术、数据科学与大数据技术、电子信息工程、通信工程、网络工程、物联网工程、自动化、电气工程、汉语言文学、法学、英语、数学、物理学、化学、生物科学、心理学、教育学。
- `concerns`：识别录取概率、专业分数线、就业前景、宿舍、学费、转专业、保研、考研、校园环境、地理位置、招生计划、招生群、联系方式。
- `contactIntent`：学生询问招生群、联系方式、电话、老师微信、怎么联系、报名时为 `true`。

专业别名归一化示例：

- `AI` -> `人工智能`
- `计算机` -> `计算机科学与技术`
- `大数据` -> `数据科学与大数据技术`
- `电子信息` -> `电子信息工程`

## 6. 学生意向评分规则

`calculateIntentScore(profile, latestInfo)` 使用 0 到 100 分规则：

- 提供分数：+20
- 提供省份：+10
- 提供科类：+10
- 明确意向专业：+20
- 询问录取概率或专业分数线：+15
- 多轮咨询：+10
- 询问报名、招生群、联系方式：+15

`getIntentLevel(score)`：

- `>= 70`：`high`
- `40 - 69`：`medium`
- `< 40`：`low`

## 7. 标签体系

`generateStudentTags(profile)` 生成可读标签：

- 地域标签：`广东考生`
- 科类标签：`物理类`
- 分数标签：`585分`
- 意向等级：`高意向`、`中意向`、`低意向`
- 专业标签：`关注人工智能`、`关注软件工程`
- 关注点标签：`关注录取概率`、`关注专业分数线`
- 联系标签：`有联系意向`

## 8. 报告统计 JSON 结构

`ConsultationReport`：

```json
{
  "tenantId": "tenant_scnu",
  "generatedAt": "2026-06-17T00:02:00+00:00",
  "totalStudents": 3,
  "highIntentCount": 1,
  "mediumIntentCount": 2,
  "lowIntentCount": 0,
  "hotMajors": [{ "name": "人工智能", "count": 1 }],
  "hotConcerns": [{ "name": "录取概率", "count": 1 }],
  "provinceDistribution": [{ "name": "广东", "count": 1 }],
  "scoreRangeDistribution": [
    { "range": "600分以上", "count": 0 },
    { "range": "580-599", "count": 1 },
    { "range": "560-579", "count": 1 },
    { "range": "540-559", "count": 0 },
    { "range": "520-539", "count": 1 },
    { "range": "500-519", "count": 0 },
    { "range": "500分以下", "count": 0 },
    { "range": "未知", "count": 0 }
  ]
}
```

## 9. 对接 B 任务 AI 咨询模块

B 组的 AI 咨询模块可以在每轮问答完成后调用：

```python
processConsultationTurn(
    store,
    tenantId="tenant_scnu",
    studentId="stu_demo_001",
    sessionId="session_demo_001",
    userMessage=user_message,
    aiReply=ai_reply,
)
```

当前规则提取可以作为保底逻辑。后续接入 DeepSeek 后，建议把 `extractStudentInfo` 替换或扩展为 LLM JSON 抽取：

- 输入：最近 N 轮对话、当前用户问题、AI 回复。
- 输出：与 `ExtractedStudentInfo` 字段一致的 JSON。
- 合并：继续复用 `updateStudentProfile`，避免 LLM 输出直接覆盖已有画像。
- 存储：继续通过 `DataLinkStore` 协议写入，保持调用方稳定。

## 10. 对接 A 任务数据库模块

A 组数据库模块可以根据当前 JSON 字段建表：

- `chat_sessions`：`sessionId`、`tenantId`、`studentId`、`startedAt`、`updatedAt`。
- `chat_messages`：`id`、`tenantId`、`studentId`、`sessionId`、`role`、`content`、`createdAt`。
- `student_profiles`：`studentId`、`tenantId`、`province`、`subjectType`、`score`、`rank`、`interestedMajors`、`concerns`、`contactIntent`、`tags`、`intentScore`、`intentLevel`、`consultationCount`、`firstConsultedAt`、`lastConsultedAt`。
- `consultation_reports`：可以按 `tenantId` 和 `generatedAt` 保存快照，也可以后台实时聚合。

替换存储时，只需实现 `DataLinkStore` 协议中的方法：`get_session`、`upsert_session`、`get_profile`、`upsert_profile`、`list_profiles`、`list_sessions`、`save_report`。

## 11. 如何进行手动输入测试

可以运行交互式本地测试脚本，手动输入学生咨询内容和 AI 回复，实时查看提取结果、画像更新结果和报告摘要：

```bash
npm run data-link:interactive
```

脚本启动后会提示输入 `tenantId`、`studentId`、`sessionId`。直接回车会使用默认值：

- `tenantId`: `tenant_scnu`
- `studentId`: `stu_manual_001`
- `sessionId`: `session_manual_001`

示例输入：

```text
学生输入 userMessage: 我是广东物理类考生，585分，想问人工智能专业稳不稳？
AI 回复 aiReply: 你的分数有一定竞争力，可以关注人工智能和软件工程。

学生输入 userMessage: 那宿舍怎么样？可以转专业吗？
AI 回复 aiReply: 学校宿舍条件整体较好，转专业需要满足学院相关要求。
```

第二轮完成后，`profile` 会保留第一轮提取到的 `province`、`subjectType`、`score`、`interestedMajors`，并合并新增的 `宿舍`、`转专业` 等 `concerns`。

交互脚本使用单独目录 `data/manual_test/` 保存 JSON 文件，避免覆盖 `data/mock/` 下的正式 demo 输出。输入 `exit`、`quit`，或在学生输入处直接回车，即可结束脚本。

## 12. AI 结构化抽取设计

当前数据链路保留规则提取，同时新增 AI 结构化抽取能力。原因是两类能力互补：

- 规则提取稳定、无需 API key、适合 demo、测试和离线环境兜底。
- AI 提取更适合处理自然语言中的复杂表达，例如风险偏好、隐含关注点、AI 回复中推荐的专业等。

### 12.1 Extractor 结构

当前实现包含三类提取器：

- `RuleBasedExtractor`：复用原有 `extractStudentInfo` 规则逻辑，并合并 userMessage 与 aiReply 中的专业、关注点。
- `LLMExtractor`：调用外部 OpenAI-compatible LLM API，要求模型只返回 JSON，再通过 `normalize_llm_extracted_info` 清洗为 `ExtractedStudentInfo`。
- `HybridExtractor`：默认提取器。启用 LLM 且存在 API key 时优先调用 LLM；LLM 不可用、请求失败、JSON 解析失败或字段不合法时，自动回退到规则提取。

Hybrid 流程：

```text
userMessage + aiReply
  -> DATA_LINK_LLM_ENABLED=true 且 DATA_LINK_LLM_API_KEY 存在？
  -> 是：尝试 LLMExtractor
  -> LLM 成功：返回 extractor="llm"
  -> LLM 失败：打印 warning，回退 RuleBasedExtractor，返回 extractor="rule_fallback"
  -> 否：使用 RuleBasedExtractor，返回 extractor="rule"
```

### 12.2 环境变量配置

`.env.example` 已提供示例配置：

```bash
DATA_LINK_LLM_ENABLED=false
DATA_LINK_LLM_PROVIDER=deepseek
DATA_LINK_LLM_API_KEY=
DATA_LINK_LLM_BASE_URL=https://api.deepseek.com/v1/chat/completions
DATA_LINK_LLM_MODEL=deepseek-chat
DATA_LINK_LLM_TIMEOUT=20
```

开启 LLM 提取时，将 `DATA_LINK_LLM_ENABLED` 设为 `true`，并填写真实 `DATA_LINK_LLM_API_KEY`。不要把真实 key 提交到仓库。

没有 API key 时，`npm run data-link:demo`、`npm run data-link:interactive`、`npm run test:data-link` 都会继续正常运行，并自动使用规则提取。

### 12.3 LLM JSON 清洗与校验

`normalize_llm_extracted_info(raw)` 会处理：

- markdown 代码块中的 JSON，例如 ```json。
- `score`、`rank` 转为 int 或 None。
- `interestedMajors`、`concerns`、`intentSignals` 保证为 list。
- `confidence` 限制在 0 到 1。
- `concerns` 和 `interestedMajors` 去重。
- `concerns` 尽量归一到录取概率、专业分数线、就业前景、宿舍、学费、转专业、保研、校园环境、招生政策、报名方式、招生联系方式。

LLM 没提到的字段不会清空旧画像。画像合并仍由 `updateStudentProfile` 负责。

### 12.4 在 interactive 中验证

运行：

```bash
npm run data-link:interactive
```

启动后会显示：

```text
当前提取模式：hybrid
LLM enabled: true/false
LLM key found: true/false
```

每轮处理完成后会显示：

```text
本轮提取方式 extractor: rule / llm / rule_fallback
```

可以用以下样例验证：

```text
学生输入 userMessage: 我是广东物理类，585分，想冲人工智能，但是怕滑档，也想问宿舍怎么样。
AI 回复 aiReply: 你的分数有竞争力，可以关注人工智能和软件工程，录取概率需要结合往年分数线和位次判断。
```

无 key 时应看到 `extractor: rule`；配置 LLM 且调用成功时应看到 `extractor: llm`；配置了 key 但请求失败时应看到 `extractor: rule_fallback`。

### 12.5 当前限制

- LLM 结构化抽取需要外部 API key。
- LLM 输出可能不稳定，因此必须保留规则兜底。
- 当前 AI 抽取只负责结构化学生画像，不负责生成招生咨询回答。
- 单元测试使用 fake LLM client，不真实请求外部 API。

## 13. 当前本地 JSON 版本限制

- 默认无 API key 时使用规则匹配；开启 LLM 后可做结构化抽取，但仍依赖外部模型稳定性。
- 本地 JSON 不是并发安全数据库，不适合多进程生产写入。
- 统计报告每轮全量重算，数据量很大时需要改为数据库聚合。
- 当前未接入真实登录鉴权，`studentId` 由调用方传入。
- 当前 `tenantId` 已保留，但 demo 只覆盖 `tenant_scnu` 一个租户。
