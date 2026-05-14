# 情感分析 + 推荐反馈 Implementation Plan

> **For agentic workers:** Use subagent-driven-development per task.

**Goal:** Add keyword-based emotion detection to guide conversation tone, and add thumbs-up/down feedback on recommendations to improve future ranking.

**Tech Stack:** Python keyword matching, PostgreSQL JSONB, React state

---

### Task 1: Emotion detection in conversation agent

**Files:** Modify `backend/agents/conversation/agent.py`

- [ ] **Step 1: Add emotion keywords and detection function**

Add this before `conversation_node`:

```python
_EMOTION_KW = {
    "焦虑": ["好烦", "担心", "紧张", "不知道怎么办", "压力", "害怕", "考砸", "万一", "怎么办"],
    "迷茫": ["不知道", "随便", "都行", "没什么想法", "无所谓", "不清楚", "不太了解", "没想过"],
    "确定": ["就想学", "一定要", "必须", "确定了", "肯定是", "就是喜欢", "非它不可"],
    "烦躁": ["别问了", "不想说", "烦死了", "随便吧", "不想聊", "就这样吧"],
    "兴奋": ["特别喜欢", "超级喜欢", "太棒了", "好期待", "梦想", "真的很喜欢"],
}

_EMOTION_HINTS = {
    "焦虑": "该学生表现出焦虑情绪，请先简短安抚（1句话），再温和提问。",
    "迷茫": "该学生比较迷茫，请用具体的例子或场景来引导，避免开放式提问。",
    "确定": "该学生目标明确，可直接追问动机来源，深度挖掘为什么喜欢。",
    "烦躁": "该学生有些不耐烦，请简短回复表示理解，给对方空间，不要追问。",
    "兴奋": "该学生表现出兴奋，请鼓励ta多说，追问更多细节和感受。",
}

def _detect_emotion(user_msg: str) -> str | None:
    for emotion, keywords in _EMOTION_KW.items():
        if any(kw in user_msg for kw in keywords):
            return emotion
    return None
```

- [ ] **Step 2: Inject emotion hint into System Prompt**

In `conversation_node`, after building the `system` message, check for emotion:

```python
    system = SystemMessage(content=SYSTEM_PROMPT.format(stage=state["stage"].value, slots_summary=summary))
    
    # Detect emotion and adjust prompt
    emotion = _detect_emotion(last_user)
    if emotion:
        hint = _EMOTION_HINTS[emotion]
        system.content += f"\n\n## 情绪提示\n{hint}"
    
    msgs = [system] + state["messages"]
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/conversation/agent.py
git commit -m "feat: add keyword-based emotion detection to conversation agent"
```

---

### Task 2: Recommendation feedback model + API

**Files:**
- Create: `backend/models/recommendation_feedback.py`
- Modify: `backend/models/__init__.py`
- Modify: `backend/api/routes/recommendation.py`
- Modify: `backend/services/recommendation_service.py`

- [ ] **Step 1: Create feedback model**

`backend/models/recommendation_feedback.py`:
```python
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from . import Base

class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    college_name: Mapped[str] = mapped_column(String(200))
    major_name: Mapped[str] = mapped_column(String(200))
    feedback_type: Mapped[str] = mapped_column(String(20))  # 'useful' | 'not_relevant'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Register in models/__init__.py**

Add to the imports:
```python
from models.recommendation_feedback import RecommendationFeedback
```

- [ ] **Step 3: Add POST /feedback endpoint**

In `backend/api/routes/recommendation.py`, add new route:

```python
from models.recommendation_feedback import RecommendationFeedback

@router.post("/feedback")
async def submit_feedback(
    body: dict,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fb = RecommendationFeedback(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user["user_id"]),
        college_name=body.get("college_name", ""),
        major_name=body.get("major_name", ""),
        feedback_type=body.get("feedback_type", "useful"),
    )
    db.add(fb)
    await db.commit()
    return {"status": "ok"}
```

Add import at top: `import uuid`

- [ ] **Step 4: Inject feedback into ranking prompt**

In `backend/services/recommendation_service.py`, in `generate_recommendations`, before building the prompt, query feedback:

```python
    # Query user feedback history
    from models.recommendation_feedback import RecommendationFeedback
    feedback_result = await db.execute(
        select(RecommendationFeedback).where(
            RecommendationFeedback.user_id == uuid.UUID(user_id)
        ).order_by(RecommendationFeedback.created_at.desc()).limit(20)
    )
    feedbacks = feedback_result.scalars().all()
    
    feedback_text = ""
    if feedbacks:
        liked = [f for f in feedbacks if f.feedback_type == "useful"]
        disliked = [f for f in feedbacks if f.feedback_type == "not_relevant"]
        if liked:
            feedback_text += f"- 之前标记为有用：{', '.join(f'{f.major_name}({f.college_name})' for f in liked[:5])}\n"
        if disliked:
            feedback_text += f"- 之前标记为不相关：{', '.join(f'{f.major_name}({f.college_name})' for f in disliked[:5])}\n"
        if feedback_text:
            feedback_text = "## 学生历史反馈\n" + feedback_text + "请参考此反馈，提升与"有用"类型相似的结果排序，降低与"不相关"类型相似的结果。\n"
    
    prompt = RANKING_PROMPT.format(profile=profile_text, candidates=candidate_text)
    if feedback_text:
        prompt = prompt.replace("## 要求", feedback_text + "## 要求")
```

Add `uuid` import at top if not already present.

- [ ] **Step 5: Commit**

```bash
git add backend/models/recommendation_feedback.py backend/models/__init__.py backend/api/routes/recommendation.py backend/services/recommendation_service.py
git commit -m "feat: add recommendation feedback model, API, and prompt injection"
```

---

### Task 3: Frontend feedback buttons

**Files:**
- Modify: `frontend/src/components/recommendation/RecommendationCard.tsx`
- Modify: `frontend/src/services/recommendation.ts`

- [ ] **Step 1: Add submitFeedback API**

In `frontend/src/services/recommendation.ts`:
```ts
export const recApi = {
  getRecommendations: () => api.get('/recommendations'),
  submitFeedback: (collegeName: string, majorName: string, feedbackType: string) =>
    api.post('/recommendations/feedback', { college_name: collegeName, major_name: majorName, feedback_type: feedbackType }),
}
```

- [ ] **Step 2: Add feedback buttons to card**

In `RecommendationCard.tsx`, add state and buttons after the expandable reasons section:

```tsx
// Add state
const [feedback, setFeedback] = useState<string | null>(null)

// Add after the </div> that closes the expandable section
{!feedback && (
  <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
    <button
      onClick={() => { recApi.submitFeedback(rec.college_name, rec.major_name, 'useful'); setFeedback('useful') }}
      className="text-xs px-3 py-1 rounded-full bg-green-50 text-green-600 hover:bg-green-100 transition"
    >
      👍 有用
    </button>
    <button
      onClick={() => { recApi.submitFeedback(rec.college_name, rec.major_name, 'not_relevant'); setFeedback('not_relevant') }}
      className="text-xs px-3 py-1 rounded-full bg-gray-50 text-gray-500 hover:bg-gray-100 transition"
    >
      👎 不相关
    </button>
  </div>
)}
{feedback === 'useful' && <div className="text-xs text-green-600 mt-2">已标记为有用</div>}
{feedback === 'not_relevant' && <div className="text-xs text-gray-400 mt-2">已标记为不相关</div>}
```

Add import at top: `import { recApi } from '../../services/recommendation'`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/recommendation/RecommendationCard.tsx frontend/src/services/recommendation.ts
git commit -m "feat: add thumbs up/down feedback buttons on recommendation cards"
```
