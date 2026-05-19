# Session B: 输出路由（双 Agent 智能路由）

> 分支: `feat/dual-agent` | 基于: `develop` | 仅改 backend

## 启动

```bash
git checkout develop && git checkout -b feat/dual-agent
```

必读: `docs/superpowers/specs/2026-05-19-optimization-design.md` §B

## 任务

### 修改 `backend/api/routes/chat.py`

在消息处理段（`user_content` 获取后、LLM 调用前）插入消息类型判断：

```python
FACTUAL_KW = ["分数线", "多少分", "位次", "就业", "薪资", "课程", "宿舍",
               "食堂", "学费", "转专业", "考研", "保研", "实验室", "奖学金"]
PSYCH_KW  = ["喜欢", "担心", "害怕", "迷茫", "不知道", "纠结", "压力",
               "爸妈", "父母", "兴趣", "性格", "适合", "讨厌"]

def classify_message(text: str) -> str:
    """Return 'factual' or 'personal' based on keyword matching."""
    if any(kw in text for kw in FACTUAL_KW):
        return "factual"
    if any(kw in text for kw in PSYCH_KW):
        return "personal"
    return "personal"  # default to personal (conversational)

msg_type = classify_message(user_content)

# Select temperature based on message type
if msg_type == "factual":
    session_llm.temperature = 0.3
else:
    session_llm.temperature = 0.7
```

提示词不变——B2B prompt 已经覆盖两者。温度控制足够区分风格。

### 不碰

- 不改 LangGraph agent 代码
- 不改 prompts.py / prompts_b2b.py
- 不改 mini-app / admin-spa

## 完成标志

- [ ] 问"计算机专业分数线"→ AI 回答精确、少废话 (temp 0.3)
- [ ] 说"我喜欢动手"→ AI 回应温暖、引导探索 (temp 0.7)
