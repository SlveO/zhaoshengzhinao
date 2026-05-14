# 质量加固：Prompt 优化 + 稳定性升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve conversation agent's contextual relevance (Chinese gaokao scenario) and add system resiliency (API retry, timeout fallback, caching, error boundaries).

**Architecture:** Two independent workstreams: (A) Prompt engineering — rewrite SYSTEM_PROMPT with gaokao-specific context, expand FEW_SHOT from 3 to 8, adjust slot extraction priority; (B) Stability — add tenacity retry to DeepSeek calls, asyncio timeout fallback for recommendations, Redis result cache, React ErrorBoundary.

**Tech Stack:** DeepSeek API, LangChain, tenacity, Redis, React 18 ErrorBoundary

---

## File Structure

```
backend/
├── agents/conversation/prompts.py          ← MODIFY: rewrite SYSTEM_PROMPT + 8 FEW_SHOT
├── agents/conversation/agent.py            ← MODIFY: slot extraction priority
├── services/recommendation_service.py      ← MODIFY: tenacity retry + asyncio timeout
├── api/routes/recommendation.py            ← MODIFY: Redis cache get/set
└── requirements.txt                        ← MODIFY: add tenacity

frontend/src/
├── components/common/ErrorBoundary.tsx     ← CREATE: error boundary component
└── App.tsx                                 ← MODIFY: wrap routes with ErrorBoundary
```

---

### Task 1: Rewrite SYSTEM_PROMPT with Gaokao Context + 8 FEW_SHOT

**Files:**
- Modify: `backend/agents/conversation/prompts.py`

- [ ] **Step 1: Replace SYSTEM_PROMPT**

Replace the entire content of `prompts.py` with the enhanced version below. This adds gaokao-specific context paragraph, 冲稳保 concept, and expands FEW_SHOT from 3 to 8 examples.

```python
SYSTEM_PROMPT = """你是一位经验丰富的高考志愿填报心理咨询师。你的任务是通过对话引导学生深入认识自己的兴趣、价值观和偏好，而不是直接给出志愿建议。

## 核心原则
1. 保持中立和共情——不要评判学生的任何选择
2. 引导而非灌输——通过提问帮助学生自己发现答案
3. 永远不要说"你应该选XX专业"——你的角色是帮助学生了解自己
4. 关注学生的情绪状态，及时调整对话节奏

## 学生背景
你面对的是中国高三毕业生。他们刚经历高考，可能处于以下状态：
- 分数焦虑：担心分数不够上理想学校
- 家长期望压力：父母的意愿可能与自己的兴趣冲突
- 信息过载：对大学专业了解有限，容易被"热门专业"误导
- 同伴比较：同学的选择可能影响自己的判断
理解这些压力，在对话中给予适当的共情和疏导。不要评判学生对分数的焦虑——这是真实的社会压力。

## 志愿策略常识（仅用于对话理解参考，不可作为建议给出）
- 冲刺：录取位次略高于学生位次的院校（录取概率较低但值得尝试）
- 稳妥：录取位次与学生位次接近的院校（录取概率较高）
- 保底：录取位次明显低于学生位次的院校（录取非常安全）

## 对话阶段
你当前处于 {stage} 阶段。各阶段目标和话术要求：

### 建立信任 (open)
- 目标：破冰，了解学生基本情况
- 话术：温暖、开放、非评判
- 示例："不管这次考试结果怎么样，我们先聊聊你对未来的想法吧"

### 深度探索 (explore)
- 目标：挖掘兴趣倾向(RIASEC)、价值观、地域偏好、家庭影响
- 话术：引导性提问，避免暗示性提问
- 关键信息：喜欢什么学科？课外做什么？对什么好奇？理想的生活状态？

### 聚焦澄清 (focus)
- 目标：在矛盾或模糊处深入澄清，确定优先级
- 话术：结构化对比，"如果必须在A和B之间选一个..."
- 方法：两难情境、权重排序、假设性提问

### 画像确认 (confirm)
- 目标：输出用户画像让学生确认或修正
- 话术：总结性，可视化反馈
- 说明各项画像维度的含义，询问是否准确

## 已收集的学生信息
{slots_summary}

## 输出格式
每次回复的末尾，附加一个隐藏的 JSON 块来更新学生画像。格式必须严格如下：
<!--SLOTS-->
{{
  "score": 数字或null,
  "subjects": "选科组合或null",
  "riasec_update": {{"R":评分,"I":评分,"A":评分,"S":评分,"E":评分,"C":评分}},
  "values_hint": "价值观关键词",
  "region_pref": ["地区"],
  "career_vision": "职业憧憬",
  "family_influence": "low/medium/high"
}}
<!--/SLOTS-->

RIASEC 维度：R=动手操作 I=研究思考 A=艺术创造 S=帮助他人 E=领导说服 C=规范有序
评分范围 1-10，只包含本轮对话中学生明确表现出的维度

## 注意事项
- 每次回复控制在2-4句话
- 一次只问一个问题
- 如果学生表达困惑或焦虑，先共情再提问
- 学生信息已通过注册表收集（如已显示分数/选科则不需要再问）
"""

FEW_SHOT_EXAMPLES = [
    {
        "type": "迷茫型",
        "user": "我也不知道喜欢什么，感觉什么都差不多",
        "response": "没关系的，很多同学在这个阶段都会有类似的感受。我们换个角度：你平时空闲的时候，做什么事情会让你感觉时间过得特别快？",
    },
    {
        "type": "主见型",
        "user": "我就是想学医，其他的不考虑",
        "response": "对医学有这么明确的方向很好。能跟我分享一下，是什么让你对医学产生兴趣的？是某个经历、某个榜样，还是别的什么？",
    },
    {
        "type": "焦虑型",
        "user": "我爸妈让我学金融，但我数学不太好，好烦",
        "response": "我能感受到你有些纠结。父母的期望和自己的实际情况之间确实需要平衡。除了数学方面的顾虑，你对金融本身感兴趣吗？",
    },
    {
        "type": "纠结型",
        "user": "我爸妈想让我学计算机，说好就业，但我自己对历史更感兴趣",
        "response": "这是个很典型的矛盾——务实的方向和内心的热爱。我们先不谈就业，你平时看历史书或者历史纪录片的时候，是什么最吸引你？",
    },
    {
        "type": "务实型",
        "user": "说实话我就想知道哪个专业以后好找工作，工资高",
        "response": "关心就业前景是非常现实的考量，这完全没问题。除了薪资和发展之外，你能接受一份虽然收入不错但每天重复枯燥的工作吗？还是说你希望工作中有一些变化和挑战？",
    },
    {
        "type": "外向型",
        "user": "我就喜欢跟人聊天打交道，坐不住办公室那种",
        "response": "喜欢社交是很好的特质。你是更喜欢一对一的深入交流，还是一对多的演讲、组织活动？这两种社交方式对应的职业方向差别挺大的。",
    },
    {
        "type": "内向型",
        "user": "我不太喜欢跟人社交，更喜欢一个人安安静静做自己的事",
        "response": "了解自己的节奏很重要。你一个人做事的时候，更享受分析和解决复杂问题（比如解数学题），还是更享受创造和表达（比如写文章、做设计）？",
    },
    {
        "type": "探索型",
        "user": "我对很多东西都有点兴趣，但都不太深入，感觉很浮躁",
        "response": "好奇心广泛不是浮躁，说明你是一个对世界保持开放的人。我们不妨反过来问：有没有什么事情是你试过之后明确知道自己不喜欢的？排除法有时候比寻找法更有效。",
    },
]
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/conversation/prompts.py
git commit -m "feat: rewrite SYSTEM_PROMPT with gaokao context, expand FEW_SHOT 3->8"
```

---

### Task 2: Slot extraction priority adjustment

**Files:**
- Modify: `backend/agents/conversation/agent.py`

- [ ] **Step 1: Adjust `_parse_response` to prioritize LLM output over keyword fallback**

The current code puts LLM `<!--SLOTS-->` and keyword fallback on equal footing. Change to: try LLM first, only use keywords if LLM produced nothing useful.

Read `backend/agents/conversation/agent.py`, find the `_parse_response` function, and modify it to track whether LLM extraction succeeded:

```python
def _parse_response(text: str, current_slots: dict, user_msg: str) -> tuple[str, dict, bool]:
    """Parse AI response. Returns (clean_text, slots, llm_extracted).
    llm_extracted=True means LLM provided slots, skip keyword fallback."""
    match = _SLOT_PATTERN.search(text)
    if match:
        try:
            update = json.loads(match.group(1))
            clean_text = _SLOT_PATTERN.sub('', text).strip()
            # Only count as LLM extraction if it actually contains data
            has_data = any(
                update.get(k)
                for k in ["score", "subjects", "riasec_update", "values_hint", "region_pref", "career_vision", "family_influence"]
            )
            if has_data:
                return clean_text, merge_slots(current_slots, update), True
        except (json.JSONDecodeError, TypeError):
            pass

    # LLM didn't produce useful SLOTS block — use keyword fallback
    fallback = _fallback_extract(user_msg)
    if fallback:
        return text.strip(), merge_slots(current_slots, fallback), False

    return text.strip(), current_slots, False
```

Then update `conversation_node` to use the new return signature:

```python
async def conversation_node(state: ConversationState) -> dict:
    summary = slots_summary(state["slots"])
    system = SystemMessage(content=SYSTEM_PROMPT.format(stage=state["stage"].value, slots_summary=summary))
    msgs = [system] + state["messages"]

    last_user = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage):
            last_user = m.content
            break

    response = await llm.ainvoke(msgs)
    clean_text, new_slots, _ = _parse_response(response.content, state["slots"], last_user)
    response.content = clean_text
    return {"messages": [response], "slots": new_slots}
```

- [ ] **Step 2: Commit**

```bash
git add backend/agents/conversation/agent.py
git commit -m "feat: prioritize LLM SLOTS output over keyword fallback"
```

---

### Task 3: DeepSeek retry + recommendation timeout

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/services/recommendation_service.py`

- [ ] **Step 1: Add tenacity to requirements**

Append to `backend/requirements.txt`:
```
tenacity==9.1.2
```

- [ ] **Step 2: Add retry + timeout to recommendation service**

Modify `backend/services/recommendation_service.py`:

Add imports at top:
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
```

Add retry decorator to the LLM call section. Replace the `response = await llm.ainvoke(prompt)` line and surrounding code inside `generate_recommendations`:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((Exception,)),
    reraise=True,
)
async def _call_llm_with_retry(prompt: str):
    return await llm.ainvoke(prompt)


async def generate_recommendations(user_id: str, profile: dict, db: AsyncSession) -> list[dict]:
    # Phase 1: retrieve candidates
    candidates = await retrieve_candidates(profile, db, k=30)

    # Phase 2: build candidate summary for LLM
    candidate_text = "\n".join(
        f"- {c['metadata']['college_name']} | {c['metadata']['major_name']} | {c['metadata']['level']} | 最低位次: {c['metadata']['min_rank']} | 最低分数: {c['metadata']['min_score']} | 选科: {c['metadata']['subjects']} | 来源: {c['metadata'].get('source_url', '')}"
        for c in candidates
    )
    profile_text = json.dumps(profile, ensure_ascii=False)
    prompt = RANKING_PROMPT.format(profile=profile_text, candidates=candidate_text)

    # LLM call with retry + timeout
    try:
        response = await asyncio.wait_for(
            _call_llm_with_retry(prompt),
            timeout=30,
        )
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("\n```", 1)[0]
        recommendations = json.loads(content)
    except (asyncio.TimeoutError, json.JSONDecodeError, Exception):
        recommendations = []
        print(f"Recommendation generation failed or timed out for user {user_id}")

    # Save to DB
    rec = Recommendation(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        profile_version=1,
        result_json=recommendations,
    )
    db.add(rec)
    await db.commit()

    return recommendations
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt backend/services/recommendation_service.py
git commit -m "feat: add DeepSeek retry (tenacity) + 30s timeout fallback for recommendations"
```

---

### Task 4: Redis recommendation cache

**Files:**
- Modify: `backend/api/routes/recommendation.py`

- [ ] **Step 1: Add cache get/set to recommendation endpoint**

Modify `backend/api/routes/recommendation.py`:

Add imports:
```python
import json as json_module
import redis.asyncio as aioredis
from config import settings
```

Add cache helper and modify `get_recommendations`:

```python
async def _get_cached_recommendations(user_id: str) -> dict | None:
    try:
        r = aioredis.from_url(settings.redis_url)
        data = await r.get(f"recs_cache:{user_id}")
        if data:
            return json_module.loads(data)
    except Exception:
        pass
    return None


async def _cache_recommendations(user_id: str, data: dict, ttl: int = 600):
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.setex(f"recs_cache:{user_id}", ttl, json_module.dumps(data, ensure_ascii=False))
    except Exception:
        pass


@router.get("", response_model=RecommendationResponse)
async def get_recommendations(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    # Check cache first
    cached = await _get_cached_recommendations(user["user_id"])
    if cached:
        return cached

    # Get profile from conversation (may be empty)
    profile_data = await get_latest_profile(db, user["user_id"])
    profile = profile_data["profile"] if profile_data else {}

    # Fallback: merge user registration data into profile
    async with async_session() as db2:
        result = await db2.execute(select(User).where(User.id == user["user_id"]))
        u = result.scalar_one_or_none()
        if u:
            if not profile.get("score") and u.score:
                profile["score"] = u.score
            if not profile.get("subjects") and u.subjects:
                profile["subjects"] = u.subjects
            if not profile.get("region_pref") and u.region:
                profile["region_pref"] = [u.region]

    recs = await generate_recommendations(user["user_id"], profile, db)
    result = {"recommendations": recs, "profile_snapshot": profile}
    
    # Cache result
    await _cache_recommendations(user["user_id"], result)
    
    return result
```

- [ ] **Step 2: Commit**

```bash
git add backend/api/routes/recommendation.py
git commit -m "feat: add Redis cache for recommendations (TTL 10min)"
```

---

### Task 5: React ErrorBoundary

**Files:**
- Create: `frontend/src/components/common/ErrorBoundary.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create ErrorBoundary component**

`frontend/src/components/common/ErrorBoundary.tsx`:
```tsx
import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
          <div className="text-center max-w-md">
            <div className="text-4xl mb-4">!</div>
            <h2 className="text-xl font-semibold text-text mb-2">页面出现异常</h2>
            <p className="text-muted text-sm mb-6">请刷新页面重试，或返回首页</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-2 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition"
              >
                刷新页面
              </button>
              <button
                onClick={() => { window.location.href = '/' }}
                className="px-6 py-2 border border-border text-text rounded-lg font-semibold hover:bg-gray-50 transition"
              >
                返回首页
              </button>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
```

- [ ] **Step 2: Wrap routes in App.tsx**

Read `frontend/src/App.tsx` and wrap the `<Routes>` with `<ErrorBoundary>`:

```tsx
import ErrorBoundary from './components/common/ErrorBoundary'

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/chat" element={<Chat />} />
            <Route path="/recommendations" element={<Recommendations />} />
          </Route>
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/common/ErrorBoundary.tsx frontend/src/App.tsx
git commit -m "feat: add React ErrorBoundary with refresh/redirect fallback UI"
```

---

## Summary

```
Task 1: Rewrite SYSTEM_PROMPT + 8 FEW_SHOT         (prompts.py)
Task 2: Slot extraction priority                    (agent.py)
Task 3: DeepSeek retry + timeout                    (requirements.txt, recommendation_service.py)
Task 4: Redis recommendation cache                  (recommendation.py)
Task 5: ErrorBoundary                               (ErrorBoundary.tsx, App.tsx)
```

Tasks 1-2 and 3-5 are independent and can run in parallel. All tasks modify different files.
