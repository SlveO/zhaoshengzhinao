# 情感分析 + 推荐反馈闭环 设计方案

## 一、情感分析模块

### 1.1 目标
检测学生在对话中的情绪状态，动态调整 AI 话术策略。纯关键词驱动，不增加额外的 LLM 调用。

### 1.2 情绪分类

| 情绪 | 触发词 | 话术调整 |
|------|--------|---------|
| 焦虑 | 好烦、担心、紧张、不知道怎么办、压力、害怕、考砸 | 先安抚情绪，降低提问密度 |
| 迷茫 | 不知道、随便、都行、没什么想法、无所谓、不清楚 | 用具体例子引导，避免开放式提问 |
| 确定 | 就想学、一定要、必须、确定了、肯定是 | 直接进入深度挖掘，追问动机来源 |
| 烦躁 | 别问了、不想说、烦死了、随便吧、不想聊 | 给空间，缩短回复，表示理解 |
| 兴奋 | 特别喜欢、超级喜欢、太棒了、好期待、梦想 | 鼓励表达，追问更多细节 |

### 1.3 实现方式

在 `agent.py` 的 `conversation_node` 中，调用 LLM 之前：
1. 对用户最新消息做关键词匹配
2. 匹配到情绪 → System Prompt 末尾追加一行 `\n## 情绪提示\n{话术调整}`
3. 未匹配 → 不追加任何内容

### 1.4 改动文件

| 文件 | 改动 |
|------|------|
| `backend/agents/conversation/agent.py` | 新增 `_EMOTION_KW` 词典 + `_detect_emotion()` 函数，`conversation_node` 中调用并注入 prompt |

---

## 二、推荐反馈闭环

### 2.1 目标
学生在推荐卡片上点击"有用/不相关"后，反馈数据存储并在后续推荐中影响排序。

### 2.2 数据模型

```sql
recommendation_feedback (
    id UUID PK,
    user_id UUID,
    college_name TEXT,
    major_name TEXT,
    feedback_type TEXT,  -- 'useful' | 'not_relevant'
    created_at TIMESTAMP
)
```

### 2.3 反馈影响方式

在 `generate_recommendations` 的 RANKING_PROMPT 中增加一段：

```
## 学生历史反馈
- 之前喜欢：临床医学（中山大学）
- 之前不喜欢：计算机科学与技术（深圳大学）

请参考此反馈，对匹配类型的结果适当提升排序。
```

### 2.4 改动文件

| 文件 | 改动 |
|------|------|
| `backend/models/recommendation_feedback.py` | 新建模型 |
| `backend/models/__init__.py` | 注册新模型 |
| `backend/api/routes/recommendation.py` | 新增 `POST /{id}/feedback` |
| `backend/services/recommendation_service.py` | 查询反馈并注入 RANKING_PROMPT |
| `frontend/src/components/recommendation/RecommendationCard.tsx` | 增加 👍/👎 按钮 |
| `frontend/src/services/recommendation.ts` | 新增 `submitFeedback()` API 调用 |

---

## 三、改动汇总

| 文件 | 操作 | 所属 |
|------|------|------|
| `backend/agents/conversation/agent.py` | 修改 | 情感分析 |
| `backend/models/recommendation_feedback.py` | 新建 | 反馈 |
| `backend/models/__init__.py` | 修改 | 反馈 |
| `backend/api/routes/recommendation.py` | 修改 | 反馈 |
| `backend/services/recommendation_service.py` | 修改 | 反馈 |
| `frontend/src/components/recommendation/RecommendationCard.tsx` | 修改 | 反馈 |
| `frontend/src/services/recommendation.ts` | 修改 | 反馈 |

共计 7 个文件，两个模块互不依赖。

## 四、验证方法

1. 情感分析：在聊天中输入"我好担心分数不够" → 检查 AI 回复是否优先安抚
2. 反馈：在推荐卡片点"有用"/"不相关" → 检查 DB 是否有记录 → 再次请求推荐是否含反馈提示
