# Session: 前端重设计

> 分支: `feat/frontend-polish` | 基于: `develop` | 单 session

## 启动

```bash
git checkout develop && git checkout -b feat/frontend-polish
```

必读: `docs/superpowers/specs/2026-05-19-frontend-redesign.md`

---

## 任务清单

### 1. AgentSettingsPage 接入 (P0) [5 min]

**文件**: `admin-spa/src/App.tsx`, `admin-spa/src/components/Sidebar.tsx`

已修复。验证存在：App.tsx 有 `<Route path="agent-settings">`，Sidebar 有 `AI 设置` 菜单项。

### 2. 学生端对比页匿名支持 (P1) [20 min]

**2a. 后端**: `backend/api/routes/compare.py` — 支持 `profile_snapshot` query param

```python
@router.get("/recommendations")
async def get_compare_recommendations(
    request: Request,
    user: dict | None = Depends(get_optional_user),
    profile_snapshot: str | None = Query(None),
):
    # priority: registered user profile > profile_snapshot param
    if user:
        profile = await get_user_profile(user["user_id"])
    elif profile_snapshot:
        profile = json.loads(profile_snapshot)
    else:
        return {"recommendations": [], "error": "No profile available"}
    # ... rest of logic
```

**2b. 前端**: `mini-app/src/pages/chat/index.vue` — 跳转时传 profile_snapshot

```javascript
function goCompare() {
  const snap = JSON.stringify(chatStore.profile);
  uni.navigateTo({ url: `/pages/compare/index?profile_snapshot=${encodeURIComponent(snap)}` });
}
```

### 3. 统一管理端 UI (P2) [30 min]

**3a. 新建 `admin-spa/src/components/StatusCard.tsx`**

```tsx
// 三态组件：loading / error / empty
export function StatusCard({ loading, error, empty, emptyMessage, children }) {
  if (loading) return <div>加载中...</div>;
  if (error) return <div>出错了: {error}</div>;
  if (empty) return <div>{emptyMessage || '暂无数据'}</div>;
  return <>{children}</>;
}
```

**3b. 新建 `admin-spa/src/components/PageHeader.tsx`**

```tsx
export function PageHeader({ title, subtitle }) {
  return (
    <div className="mb-6">
      <h2 className="text-xl font-bold text-gray-800">{title}</h2>
      {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}
```

**3c. 统一图表配色**



```tsx
const brandColor = getComputedStyle(document.documentElement)
  .getPropertyValue('--brand-primary').trim() || '#2563eb';

// 图表 option 中使用 brandColor
```

### 4. 学生端对话页增强 (P3) [20 min]

**4a. 对比按钮状态**: 画像完整度 L2+ 才可点

```vue
<text class="header-btn" 
  :class="{ disabled: !chatStore.profile || chatStore.profile.completeness === 'L1' }"
  @tap="goCompare">对比</text>
```

**4b. 阶段完成自动弹窗引导**: CONFIRM 阶段 summary 消息后追加对比引导

### 5. Build 验证 [5 min]

```bash
cd admin-spa && npm run build
cd mini-app && TENANT=scnu node build.config.js && npm run build:h5
```

---

## 完成标志

- [ ] Admin SPA `npm run build` 通过
- [ ] Mini-App `npm run build:h5` 通过
- [ ] 管理端侧边栏完整（含增强分析、AI 设置）
- [ ] AI 设置页可访问
- [ ] 匿名对话后可跳转对比页
