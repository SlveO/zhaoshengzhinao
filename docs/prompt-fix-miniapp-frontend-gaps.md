# Prompt: 修复 Mini-App 前端数据通路缺口（4 项）

将下面 `---` 之间的完整内容复制到新 Claude Code session。纯前端修复，不涉及后端。

---

> **任务**：上一轮修复了后端三层（提取 intent_majors + 推荐加分 + onShow 刷新推荐），252 测试通过。但前端没有呈现更新后的 UI。根因是 4 个数据通路缺口——后端把数据算好了，前端没有接收。
>
> **约束**：只修改前端代码（2 个文件），不修改后端。匹配现有代码风格。
>
> **执行顺序**：Task 1 → Task 2 → Task 3 → Task 4 → 验证。串行执行。

---

## 背景

后端已有但前端未接收的数据：

| 数据 | 后端来源 | 前端状态 |
|------|---------|---------|
| `profile_summary` | `POST /miniapp/enter` 响应字段 | `onLoad` 忽略 |
| `profile_updated` + `profile_summary` | SSE `done` 事件字段 | handler 忽略 |
| `GET /student/profile` | 完整 profile API | profile 页只在 `onLoad` 调一次 |

---

## Task 1: Profile 页添加 `onShow` 自动刷新

**文件**：@mini-app/src/pages/profile/index.vue

### 1.1 Import `onShow`（L97）

```typescript
// Before
import { onLoad } from "@dcloudio/uni-app"

// After
import { onLoad, onShow } from "@dcloudio/uni-app"
```

### 1.2 添加 `onShow` 钩子

在 `onLoad` 之后（L129 之后）添加：

```typescript
onShow(() => {
  loadProfile()
})
```

### 1.3 修复数据合并方式（L117-118）

当前直接赋值会覆盖 `focus_points` 默认值，改为 spread 合并：

```typescript
// Before
studentInfo.value = res.data.profile
hasProfile.value = res.data.has_profile

// After
studentInfo.value = { ...studentInfo.value, ...res.data.profile }
hasProfile.value = res.data.has_profile
```

---

## Task 2: Chat 页捕获 enter 响应中的 `profile_summary`

**文件**：@mini-app/src/pages/chat/index.vue

### 2.1 添加 profile 响应式状态

在 L159（`scrollTimer` 之后）添加：

```typescript
const profileSummary = ref<any>(null)
```

### 2.2 在 3 处 enter 调用中捕获 `profile_summary`

**位置 A** — `onLoad` 的 `if (res.data)` 块内（L189 之后，`showEntry.value = false` 之后）：

```typescript
if (res.data.profile_summary) {
  profileSummary.value = res.data.profile_summary
}
```

**位置 B** — `handleGuest` 的 `if (res.data)` 块内（L216 之后，`showEntry.value = false` 之后）：同上代码。

**位置 C** — `onLoginSuccess` 的 `if (res.data)` 块内（L239 之后，`showEntry.value = false` 之后）：同上代码。

---

## Task 3: SSE `done` 事件处理 `profile_updated` + `profile_summary`

**文件**：@mini-app/src/pages/chat/index.vue

### 3.1 改造 `done` 事件处理器（L422-428）

将当前的：
```typescript
} else if (evt.type === "done") {
  isThinking.value = false
  thinkingStatus.value = ""
  if (evt.assistant_message) {
    const msg = messages.value.find(m => m.id === aiId)
    if (msg) msg.id = evt.assistant_message.message_id || aiId
  }
}
```

扩展为：
```typescript
} else if (evt.type === "done") {
  isThinking.value = false
  thinkingStatus.value = ""
  if (evt.assistant_message) {
    const msg = messages.value.find(m => m.id === aiId)
    if (msg) msg.id = evt.assistant_message.message_id || aiId
  }
  if (evt.profile_updated && evt.profile_summary) {
    profileSummary.value = evt.profile_summary
    uni.showToast({
      title: "已更新你的咨询档案",
      icon: "success",
      duration: 2000,
    })
  }
}
```

---

## Task 4: 聊天界面添加 profile 状态指示器

**文件**：@mini-app/src/pages/chat/index.vue

### 4.1 Template 中添加浮动指示条

在 `chat-body` 内、`<scroll-view class="message-scroll">` 之前（L41 附近）添加：

```html
<view v-if="profileSummary" class="profile-indicator" @tap="goProfile">
  <text class="profile-indicator-text">
    已识别: {{ profileSummary.province || '' }} {{ profileSummary.subject_type || '' }} {{ profileSummary.score || '' }}分
  </text>
  <text class="profile-indicator-arrow">查看档案 ›</text>
</view>
```

### 4.2 添加 `goProfile` 函数

在 `scrollToBottom` 函数附近（L477 之后）添加：

```typescript
function goProfile(): void {
  uni.switchTab({ url: "/pages/profile/index" })
}
```

### 4.3 添加样式

在 `</style>` 之前（L1000 附近）添加：

```css
.profile-indicator {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 8rpx 4rpx 0;
  padding: 14rpx 24rpx;
  border-radius: 20rpx;
  background: rgba(37, 99, 235, 0.08);
  border: 1rpx solid rgba(37, 99, 235, 0.15);
}

.profile-indicator-text {
  font-size: 23rpx;
  color: #1d4ed8;
  font-weight: 600;
}

.profile-indicator-arrow {
  font-size: 23rpx;
  color: #60a5fa;
}
```

---

## 验证

### 构建

```bash
docker compose build mini-app && docker compose up -d mini-app
```

### 回归测试

```bash
docker compose exec backend python -m pytest tests/ -q --tb=short
```

### 手动 E2E

1. 访客模式进入 → 发送"我是广东物理类考生 620 分，想学计算机"
2. 等待回复 → 应收到 toast "已更新你的咨询档案"
3. 聊天页顶部应出现蓝色指示条："已识别: 广东 物理类 620分" → "查看档案 ›"
4. 点击指示条 → 切换到"我的"tab → 演示档案卡片显示：广东 / 物理类 / 620 / 计算机
5. 切换到"报考建议"tab → 考生信息卡片显示：广东 / 物理类 / 620 / 计算机
6. 切回 AI 咨询 → 说"金融专业也不错" → 切回报考建议 → 意向方向更新为"计算机 / 金融"

---

## 变更总结

| 文件 | 修改项 | 行 |
|------|--------|-----|
| `profile/index.vue` | import onShow, 添加 onShow 钩子, spread 合并数据 | L97, L129+, L117-118 |
| `chat/index.vue` | 添加 profileSummary ref（L159+） | 1 行 |
| `chat/index.vue` | 3 处 enter 响应中捕获 profile_summary（onLoad/handleGuest/onLoginSuccess） | 各 3 行 |
| `chat/index.vue` | SSE done handler 处理 profile_updated + toast（L422-428） | +7 行 |
| `chat/index.vue` | Template 添加 profile 指示条（L41 前） | 6 行 |
| `chat/index.vue` | 添加 goProfile 函数（L477+） | 4 行 |
| `chat/index.vue` | 添加 .profile-indicator 样式（L1000 前） | 20 行 |

纯前端，2 个文件，约 50 行净增。
