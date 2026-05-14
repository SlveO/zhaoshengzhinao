# UX 修复：注册简化 + 阶段修正 + 筛选修复 设计方案

## 一、注册简化 + 欢迎弹窗

### 1.1 目标
注册只收用户名+密码。分数/选科/地区改为登录后的欢迎弹窗收集，收集后仍从"建立信任"开始至少 3 轮对话才推进。

### 1.2 流程

```
注册(用户名+密码) → 登录 → /chat 页面
  → 首次进入（slots 无 score）→ 弹出 WelcomeModal
    → 填写分数/选科/地区 → 提交
      → PATCH users 表 + 注入 Redis slots
      → 弹窗关闭，AI 开场白："不管这次考试结果怎么样..."
      → 阶段 = open，open_turns = 1
  → 后续每次用户消息，open_turns += 1
  → open_turns >= 3 且 score 已收集 → 推进到 explore
```

### 1.3 改动

| 文件 | 改动 |
|------|------|
| `frontend/src/pages/Register.tsx` | 删除分数/选科/地区字段，只留用户名+密码 |
| `frontend/src/components/chat/WelcomeModal.tsx` | 新建——分数输入+选科下拉+地区下拉+提交按钮 |
| `frontend/src/pages/Chat.tsx` | 检查 `slots.score` 是否为空，为空则显示 WelcomeModal |
| `frontend/src/services/api.ts` | 新增 `updateProfile()` PATCH 调用 |
| `backend/api/routes/chat.py` | 新增 `PATCH /profile` 端点更新 users 表 + session slots；`_determine_next_stage` 的 OPEN 条件改为 `bool(score) and open_turns >= 3`；`chat_websocket` 中 open 阶段每轮 `open_turns += 1` |

### 1.4 WelcomeModal UI

```
┌──────────────────────────────────┐
│          欢迎！                  │
│    在开始之前，先了解你的基本情况   │
│                                  │
│  预估分数：[____] (如 610)        │
│  选科组合：[物理+化学+生物  ▾]    │
│  所在地区：[广东  ▾]              │
│                                  │
│        [开始对话]                 │
└──────────────────────────────────┘
```

---

## 二、阶段小结弹窗修正

### 2.1 问题
`chat.py` 发 summary 时 stage 传 `next_stage.value`（新阶段），前端弹窗显示"深度探索完成"实际刚完成的是"建立信任"。

### 2.2 修复
`solt_filler.py` `chat_websocket` 中 summary 消息的 stage 改为 `current_stage.value`：

```python
await ws.send_json({
    "type": "summary",
    "stage": current_stage.value,  # 刚完成的阶段，不是 next_stage
    "content": summary_text,
    "profile_snapshot": new_slots,
})
```

| 文件 | 改动 |
|------|------|
| `backend/api/routes/chat.py` | 1 行修改 |

---

## 三、推荐地区筛选修复

### 3.1 问题
LLM 输出的推荐 JSON 没有 `city` 字段。FilterBar 用 `r.college_name.includes("广州")` 匹配，但"华南理工大学"不含"广州"二字→被过滤掉。

### 3.2 修复

**后端：** RANKING_PROMPT 要求 LLM 在每条推荐中包含 `city` 字段
**前端：** FilterBar 改用 `r.city` 做精确匹配（不再用 college_name contains）

| 文件 | 改动 |
|------|------|
| `backend/services/recommendation_service.py` | RANKING_PROMPT 示例 JSON 加 `"city": "广州"` |
| `frontend/src/components/recommendation/FilterBar.tsx` | `r.college_name.includes(city)` → `r.city === city` |
| `frontend/src/types/index.ts` | Recommendation 接口加 `city?: string` |

---

## 四、完整文件清单

| 文件 | 操作 | 所属 |
|------|------|------|
| `frontend/src/pages/Register.tsx` | 修改 | 问题1 |
| `frontend/src/components/chat/WelcomeModal.tsx` | 新建 | 问题1 |
| `frontend/src/pages/Chat.tsx` | 修改 | 问题1 |
| `frontend/src/services/api.ts` | 修改 | 问题1 |
| `backend/api/routes/chat.py` | 修改 | 问题1+2 |
| `backend/services/recommendation_service.py` | 修改 | 问题3 |
| `frontend/src/components/recommendation/FilterBar.tsx` | 修改 | 问题3 |
| `frontend/src/types/index.ts` | 修改 | 问题3 |

## 五、验证方法

1. 注册：表单只有用户名+密码两个字段
2. 欢迎弹窗：登录后弹出，填写分数/选科/地区后开始对话
3. open 阶段：至少 3 轮对话不会推进到 explore
4. 小结弹窗：open→explore 时弹窗显示"建立信任完成"而非"深度探索完成"
5. 推荐筛选：选择"广州"后能正确显示华南理工大学等广州院校
