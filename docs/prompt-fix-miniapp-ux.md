# Prompt: 修复 Mini-App 三个 UX 问题

将下面 `---` 之间的完整内容复制到新 Claude Code session。串行执行：Task 1 → Task 2 → Task 3（每个 Task 内可并行 sub-agent）→ 验证。

---

> **任务**：修复 mini-app 三个 UX 问题。1 个纯前端，1 个纯前端，1 个全栈。
>
> **约束**：不修改不相关的代码，不引入新依赖，匹配现有代码风格。
>
> **执行顺序**：Task 1 + Task 2 可并行（互不依赖）→ Task 3（依赖 Task 1+2 完成后的上下文）→ 验证。严格串行。

---

## Task 1: 添加退出登录功能（前端，agent: mini-app-dev, model: sonnet）

**问题**：`userStore.logout()` 和 `authApi.logout()` 在 @mini-app/src/stores/user.ts:73 和 @mini-app/src/utils/api.ts:159 已定义，但从未被任何 UI 调用。用户无法退出登录来测试注册和游客功能。

**文件**：@mini-app/src/pages/profile/index.vue

**修改**：

### 1.1 Template 改动

在 `status-card` 的 button 区域（line 31-32），将原来的单一按钮结构替换为：

```html
<button v-if="userStore.isGuest" class="primary-btn" @tap="showLogin = true">登录查看完整档案</button>
<view v-else class="profile-actions">
  <button class="primary-btn" @tap="goChat">去 AI 咨询</button>
  <button class="logout-btn" @tap="handleLogout">退出登录</button>
</view>
```

### 1.2 Script 改动

在 `<script setup>` 顶部添加 import（line 96 附近）：

```typescript
import { clearStoredSessionId } from "@/utils/session"
```

session.ts 路径：@mini-app/src/utils/session.ts，`clearStoredSessionId` 函数在 line 32。

添加 `handleLogout` 函数（在 `goChat` 函数之后，line 140 附近）：

```typescript
function handleLogout(): void {
  userStore.logout()
  clearStoredSessionId()
  studentInfo.value = { province: "", subject_type: "", score: 0, intent_majors: [], focus_points: [] }
  hasProfile.value = false
  sessionId.value = null
  uni.switchTab({ url: "/pages/chat/index" })
}
```

### 1.3 Style 改动

在 `</style>` 之前添加：

```css
.profile-actions {
  width: 100%;
  margin-top: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.logout-btn {
  width: 100%;
  height: 78rpx;
  line-height: 78rpx;
  border-radius: 999rpx;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 28rpx;
  font-weight: 700;
}

.logout-btn::after {
  border: none;
}
```

### 1.4 验证标准

1. 已登录状态 → "我的" tab 显示"退出登录"按钮
2. 点击退出 → 跳转 AI 咨询页 → 显示入口浮层（注册/访客两个按钮）
3. 访客模式 → "我的" tab 显示"登录查看完整档案"（不显示退出按钮）

---

## Task 2: 修复 AI 对话自动滚动（前端，agent: mini-app-dev, model: sonnet）

**问题**：@mini-app/src/pages/chat/index.vue 的 SSE 流式输出滚动有三个缺陷：

| 子问题 | 位置 | 现象 |
|--------|------|------|
| 2a | line 428，每个 SSE chunk 都触发 `scrollToBottom()` | 滚动抖动，用户向上翻阅历史时被强制拉回底部 |
| 2b | line 302-332，轮询回退路径 | 收到回复后不滚动，新内容在视口外 |
| 2c | line 185-192，历史记录加载 | 加载历史消息后不滚动，停留在顶部 |

**文件**：@mini-app/src/pages/chat/index.vue

### 2.1 添加滚动状态追踪（在 line 154 附近，`scrollTop` ref 旁边）

```typescript
const shouldAutoScroll = ref(true)
const prevScrollTop = ref(0)
let scrollTimer: ReturnType<typeof setTimeout> | null = null
```

### 2.2 Template 改动 — scroll-view 添加事件绑定（line 42-48）

```html
<scroll-view
  class="message-scroll"
  scroll-y
  enhanced
  :bounces="false"
  :scroll-top="scrollTop"
  :scroll-with-animation="true"
  @scroll="onScroll"
  @scrolltolower="onScrollToLower"
>
```

### 2.3 添加事件处理函数（在 `scrollToBottom` 函数附近，line 446 前）

```typescript
function onScrollToLower(): void {
  shouldAutoScroll.value = true
}

function onScroll(e: any): void {
  const current = e.detail.scrollTop || 0
  if (current < prevScrollTop.value - 15) {
    shouldAutoScroll.value = false
  }
  prevScrollTop.value = current
}
```

### 2.4 改造 `scrollToBottom`（替换 line 446-450）

```typescript
function scrollToBottom(): void {
  if (!shouldAutoScroll.value) return
  if (scrollTimer) return
  scrollTimer = setTimeout(() => {
    scrollTimer = null
    nextTick(() => {
      scrollTop.value = Date.now()
    })
  }, 80)
}
```

### 2.5 发送消息时恢复自动滚动（line 290 前，`scrollToBottom()` 调用处）

```typescript
shouldAutoScroll.value = true
scrollToBottom()
```

### 2.6 轮询回退添加滚动（line 322 之后，`if (msg) msg.content = last.content` 内部）

在该 if 块末尾（line 323 `return` 之前）添加：

```typescript
scrollToBottom()
```

### 2.7 历史记录加载后滚动（line 192 之后）

在 `messages.value = ...` 赋值之后添加：

```typescript
nextTick(() => {
  scrollToBottom()
})
```

### 2.8 验证标准

1. 发送消息 → 自动滚到底部 ✓
2. SSE 流式输出时 → 滚动平滑不抖动（80ms 节流）
3. 流式输出中向上滑动 → 不再被强制拉回底部
4. 手动滚回底部 → 恢复自动跟随（`@scrolltolower` 重置标志）
5. 轮询回退模式 → 收到回复后自动滚到底部
6. 有历史记录的会话 → 加载后自动滚到底部

---

## Task 3: 修复意向方向提取 + 推荐动态刷新（全栈，两个 agent 可并行）

**问题**：@mini-app/src/pages/recommendations/index.vue 的"意向方向"始终为空，推荐专业不随咨询动态变化。根因有三层：

| 层 | 根因 | 位置 |
|----|------|------|
| 后端提取 | `extract_profile_from_message` 只提取 province/subject_type/score，不提取 `intent_majors` | @backend/services/consult_service.py:97-115 |
| 后端推荐 | `/recommendations` 端点只用 `score` 算匹配度，不使用 `intent_majors` | @backend/api/routes/miniapp.py:329-362 |
| 前端刷新 | `onShow` 只调用 `loadProfile()`，不调用 `loadRecommendations()` | @mini-app/src/pages/recommendations/index.vue:199-201 |

### Fix 3A: 后端提取 intent_majors（agent: backend-dev, model: sonnet）

**文件**：@backend/services/consult_service.py

在 `extract_profile_from_message` 函数中（line 114 之后，score 提取的 if 块之后，`return updates` 之前）插入：

```python
if not existing_profile.get("intent_majors"):
    major_keywords = [
        "计算机", "人工智能", "软件工程", "数据科学", "网络安全", "大数据",
        "电子信息", "通信工程", "自动化", "电气工程", "微电子",
        "机械", "土木", "建筑", "材料", "环境",
        "临床医学", "口腔医学", "药学", "护理",
        "法学", "经济学", "金融", "会计", "工商管理", "国际贸易",
        "数学", "物理", "化学", "生物", "地理",
        "中文", "英语", "日语", "新闻", "历史", "哲学",
        "师范", "教育", "心理", "体育",
    ]
    found = []
    for kw in major_keywords:
        if kw in text:
            found.append(kw)
    if found:
        updates["intent_majors"] = found[:5]
```

验证：`docker compose exec backend python -m pytest tests/unit/test_consult_service.py -v --tb=short`

### Fix 3B: 后端推荐接口 intent_majors 加分（agent: backend-dev, model: sonnet）

**文件**：@backend/api/routes/miniapp.py

在 `/recommendations` 端点的 items 循环内（line 329-362），重构 match_score 计算和 reasons 构建。

当前代码（line 329-362）结构：
```python
student_score = profile_snapshot.get("score", 0) or session.score or 0
items = []
for m in majors:
    if student_score > 0:
        diff = student_score - (m.min_score or 0)
        if diff >= 10:
            risk_level, risk_label = "safe", "较稳妥"
        elif diff >= -5:
            risk_level, risk_label = "match", "较匹配"
        else:
            risk_level, risk_label = "reach", "可冲"
        match_score = min(95, max(50, 70 + diff))
    else:
        risk_level, risk_label, match_score = "match", "参考", 75

    items.append({
        ...
        "match_score": match_score,
        ...
        "reasons": [
            f"该专业{risk_label}你的分数水平" if student_score > 0 else "建议填写分数后获得更精准推荐",
            "属于华南师范大学招生专业",
        ],
    })
```

替换为：

```python
student_score = profile_snapshot.get("score", 0) or session.score or 0
intent_majors = profile_snapshot.get("intent_majors", []) or []
items = []
for m in majors:
    if student_score > 0:
        diff = student_score - (m.min_score or 0)
        if diff >= 10:
            risk_level, risk_label = "safe", "较稳妥"
        elif diff >= -5:
            risk_level, risk_label = "match", "较匹配"
        else:
            risk_level, risk_label = "reach", "可冲"
        match_score = min(95, max(50, 70 + diff))
    else:
        risk_level, risk_label, match_score = "match", "参考", 75

    # Intent major boost
    if intent_majors and student_score > 0:
        for intent in intent_majors:
            if intent in (m.major_name or ""):
                match_score = min(98, match_score + 8)
                break

    reasons = [
        f"该专业{risk_label}你的分数水平" if student_score > 0 else "建议填写分数后获得更精准推荐",
        "属于华南师范大学招生专业",
    ]
    if intent_majors and student_score > 0:
        for intent in intent_majors:
            if intent in (m.major_name or ""):
                reasons.append(f"符合你的意向方向「{intent}」")
                break

    items.append({
        "id": f"rec_{m.id}",
        "college_id": f"tenant_{body.tenant_slug}",
        "college_name": "华南师范大学",
        "major_name": m.major_name,
        "province": m.province or "广东",
        "city": scnu.city or "广州",
        "level": scnu.level or "本科",
        "match_score": match_score,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "min_score": m.min_score or 0,
        "min_rank": m.min_rank or 0,
        "subjects": m.subject_requirements or "物理+不限",
        "reasons": reasons,
    })
```

### Fix 3C: 前端推荐页 onShow 同时刷新推荐（agent: mini-app-dev, model: sonnet）

**文件**：@mini-app/src/pages/recommendations/index.vue

Line 199-201，将：

```typescript
onShow(() => {
  loadProfile()
})
```

改为：

```typescript
onShow(() => {
  loadProfile()
  loadRecommendations()
})
```

### 验证标准（Fix 3A+3B+3C 全部完成后）

1. 访客模式 → AI 咨询说"我对计算机和人工智能感兴趣" → 等待回复
2. 切换到"报考建议"tab → "意向方向"显示"计算机 / 人工智能"
3. 推荐专业列表中，名称含"计算机"的专业匹配度 +8，推荐理由含"符合你的意向方向「计算机」"
4. 切回 AI 咨询 → 说"金融专业也不错" → 等待回复
5. 切回"报考建议" → "意向方向"更新为"计算机 / 人工智能 / 金融"

---

## 最终验证

Task 1+2+3 全部完成后执行：

```bash
# 重建并启动
docker compose build backend mini-app && docker compose up -d backend mini-app

# 后端回归测试
docker compose exec backend python -m pytest tests/unit/test_consult_service.py tests/integration/test_miniapp_pipeline.py -v --tb=short

# 手动验证检查点
# 1. 注册 → 我的 tab → 退出登录 → 入口浮层出现
# 2. 访客聊天 → SSE 流式滚动平滑 → 上滑不被拉回
# 3. 聊天中说意向专业 → 切到报考建议 → 意向方向已更新 → 推荐加分
```

---

## 失败处理

| 失败类型 | 处理方式 |
|----------|---------|
| CODE（业务逻辑错误） | 记录到 reports/block.md，总结到报告 |
| TEST（测试失败） | 修复 mock/assert，不修改被测代码 |
| INFRA（构建/容器） | 重试最多 2 次，仍失败记录到 reports/block.md |
