# Admin-SPA 院校管理端综合修复设计

- 日期: 2026-06-27
- 状态: Approved
- 作者: brainstorming session
- 关联: admin-spa / backend / Auth 系统

## 1. 背景与目标

院校管理后台（admin-spa）在日常使用中暴露 10 个独立问题，覆盖路由跳转、文案、交互反馈、AI 配置架构、布局、登录鉴权六个层面。本 spec 给出统一修复方案，目标是让招生老师能够顺畅使用后台，同时保留开发者账号的高级权限。

## 2. 问题清单

| # | 类别 | 问题 | 涉及文件 |
|---|---|---|---|
| 1 | 路由 | 工作台「查看全部」按钮无法跳转（用了 `#/consultations` 但项目用 BrowserRouter） | DashboardPage.tsx |
| 2 | 文案 | 「咨询工作台」需更名为「咨询管理」 | DashboardPage.tsx, Sidebar.tsx |
| 3 | 反馈 | 重新生成咨询摘要无 loading/成功/失败提示 | ConsultationsPage.tsx |
| 4 | 架构 | AI 对话配置的 custom_prompt 与提示词模板功能重复；形象提示词需咨询+推荐两个模块都调用 | AgentSettingsPage.tsx, chat.py, consult.py |
| 5 | 布局 | 提示词模板 5 项同页堆叠需滚轮 | AgentSettingsPage.tsx |
| 6 | 布局 | 知识库 Raw 左右滚轮同步，且无搜索 | KnowledgeRawTab.tsx |
| 7 | 视觉 | 侧边栏折叠按钮不够显眼 | Sidebar.tsx |
| 8 | 清理 | Header 消息铃铛是假按钮（按了无反应） | Header.tsx |
| 9 | 交互 | Header 头像按钮无反应，应为账号切换菜单 | Header.tsx |
| 10 | 鉴权 | 关闭体验入口；注册 scnu 账号；区分开发者/院校管理员权限 | LoginPage.tsx, authStore.ts, startup_seed.py |

## 3. 详细设计

### 3.1 Issue 1: 查看全部按钮跳转

**根因**: `BrowserRouter` 不识别 `#` 前缀，`<a href="#/consultations">` 被当成锚点。

**修复**:
```tsx
import { Link } from 'react-router-dom'
<Link to="/consultations" style={{ fontSize: 12, color: 'var(--color-brand-800)', textDecoration: 'none' }}>
  查看全部 →
</Link>
```

### 3.2 Issue 2: 文案更名

两处修改：
- `DashboardPage.tsx:136` Hero 标题 `招生智脑 · 咨询工作台` → `招生智脑 · 咨询管理`
- `Sidebar.tsx:23` 菜单 label `'咨询工作台'` → `'咨询管理'`

### 3.3 Issue 3: 重新生成摘要反馈

`ConsultationsPage.tsx` 新增状态：
```tsx
const [regenerating, setRegenerating] = useState(false)
const [toast, setToast] = useState<{type:'ok'|'err'; text:string}|null>(null)

async function regenerateSummary() {
  if (!selected || regenerating) return
  setRegenerating(true)
  try {
    await api.post(`/admin/consultations/${selected.session.session_id}/regenerate-summary`)
    const res = await api.get(`/admin/consultations/${selected.session.session_id}`)
    setSelected(res.data)
    setToast({type:'ok', text:'摘要已重新生成'})
  } catch (e:any) {
    setToast({type:'err', text: e?.message || '重新生成失败'})
  } finally {
    setRegenerating(false)
    setTimeout(() => setToast(null), 3000)
  }
}
```

按钮 UI：
- regenerating 期间 disabled + 文案「重新生成中...」
- 摘要内容区 regenerating 期间 opacity:0.6
- toast 浮动显示在抽屉右上角

### 3.4 Issue 4: AI 对话配置改造（核心）

#### 3.4.1 现状问题
- `custom_prompt` 是原始 textarea，本质即提示词模板，与「提示词模板」tab 重叠
- **咨询模块 consult.py:173 只读 `consult_system` 模板，未读 persona 配置**
- 推荐模块 chat.py:209 直接把 `persona["custom_prompt"]` 当 system_content 用

#### 3.4.2 PersonaConfig 字段（4 个）

| 字段 | 类型 | UI 控件 | 说明 |
|---|---|---|---|
| `assistant_name` | string | 文本输入 | AI 助手名称（如「小招」「华师招生助手」） |
| `greeting` | string | textarea(短) | 开场白/自我介绍 |
| `style` | 'casual' \| 'formal' | 单选卡片 | 亲切自然 / 正式专业 |
| `proactive_recommend` | boolean | 开关 | 是否主动推荐专业 |

**移除**: `custom_prompt` 字段（保留向后兼容降级）。

#### 3.4.3 后端改造

**新文件 `backend/services/persona_service.py`**:
```python
def build_persona_greeting(persona: dict, uni_short: str) -> str:
    """组装形象引导段（prepend 到 system prompt 前）。"""
    name = persona.get("assistant_name") or f"{uni_short}招生助手"
    greeting = persona.get("greeting", "")
    parts = [f"你的名字是「{name}」，代表 {uni_short} 招生办为学生提供咨询服务。"]
    if greeting:
        parts.append(f"开场白/自我介绍：{greeting}")
    return "\n".join(parts)

def apply_persona_style(system_content: str, persona: dict) -> str:
    """在 system prompt 末尾追加风格提示。"""
    if persona.get("style") == "formal":
        return system_content + "\n\n请使用正式、专业的语气。"
    return system_content

def has_legacy_custom_prompt(persona: dict) -> bool:
    """检测旧 custom_prompt 是否存在（迁移期降级用）。"""
    return bool(persona.get("custom_prompt"))
```

**推荐模块 `chat.py:209-252` 改造**:
```python
# 旧逻辑：if persona.get("custom_prompt"): system_content = persona["custom_prompt"].format(...)
# 新逻辑：
if has_legacy_custom_prompt(persona):
    # 迁移期降级：旧 custom_prompt 仍可用
    system_content = persona["custom_prompt"].format(stage=current_stage.value, slots_summary=slots_text)
else:
    b2b_template = await load_prompt("b2b_system", tenant_slug)
    # ... consult_context / rag_context 拼装保持不变 ...
    system_content = b2b_template.format(...)
    # 新增：prepend persona 形象引导
    persona_greeting = build_persona_greeting(persona, uni_short or uni_name)
    system_content = persona_greeting + "\n\n" + system_content
# style 追加（保持现有逻辑）
system_content = apply_persona_style(system_content, persona)
```

**咨询模块 `consult.py:173-200` 改造**（关键新增）:
```python
system_template = await load_prompt("consult_system", body.tenant_slug)
# ... slots_text / admission_table / knowledge_context 拼装保持不变 ...
system_content = system_template.format(
    slots_summary=slots_text,
    admission_table=admission_table,
    knowledge_context=knowledge_context,
)
# 新增：prepend persona 形象引导 + style 后缀
# 需先在 consult.py 中加载 tenant_config 的 ai_persona
try:
    from tenants.service import resolve_tenant as _resolve
    t = await _resolve(body.tenant_slug)
    persona = (t.config or {}).get("ai_persona", {}) if t else {}
    uni_short = (t.config or {}).get("brand", {}).get("short_name", "") if t else ""
except Exception:
    persona = {}
    uni_short = ""

if not has_legacy_custom_prompt(persona):
    persona_greeting = build_persona_greeting(persona, uni_short)
    system_content = persona_greeting + "\n\n" + system_content
    system_content = apply_persona_style(system_content, persona)
```

#### 3.4.4 前端 UI 改造（AgentSettingsPage.tsx persona tab）

移除「自定义提示词」textarea + 占位符说明，改为 4 字段表单卡片：
```
┌─ AI 对话配置 ─────────────────┐
│ AI 助手名称: [小招          ] │
│ 开场白/自我介绍:              │
│ [textarea 短                  ] │
│ 对话风格:                     │
│  [亲切自然] [正式专业]        │
│ 主动推荐: [开关] 已开启        │
│ [保存配置]                    │
└──────────────────────────────┘
```

右侧「提示词渲染预览」保留，实时展示组装后的完整 system prompt（让老师看到效果）。

#### 3.4.5 类型同步

`admin-spa/src/types/index.ts`:
```ts
export interface PersonaConfig {
  assistant_name: string
  greeting: string
  style: 'casual' | 'formal'
  proactive_recommend: boolean
  // 旧字段保留用于读旧配置（写时不再产生）
  custom_prompt?: string
}
```

`DEFAULT_PERSONA` 更新为 4 字段默认值。

### 3.5 Issue 5: 提示词模板左右布局

`AgentSettingsPage.tsx` prompts tab 改造：
```tsx
const [selectedKey, setSelectedKey] = useState<string>('')
useEffect(() => {
  if (promptKeys.length && !selectedKey) setSelectedKey(promptKeys[0])
}, [promptKeys])

<div style={{display:'flex', gap:16, minHeight:500}}>
  <div style={{width:240, borderRight:'1px solid #e5e7eb', paddingRight:12}}>
    {promptKeys.map(k => (
      <div key={k} onClick={()=>setSelectedKey(k)}
        style={{
          padding:'8px 12px', cursor:'pointer',
          background: selectedKey===k ? '#eff6ff' : 'transparent',
          borderRadius:4, marginBottom:4, fontSize:13,
          fontWeight: selectedKey===k ? 600 : 400,
        }}>
        {PROMPT_KEY_LABELS[k] || k}
      </div>
    ))}
  </div>
  <div style={{flex:1}}>
    {selectedKey && <PromptEditor key={selectedKey} promptKey={selectedKey} />}
  </div>
</div>
```

### 3.6 Issue 6: 知识库 Raw 独立滚动 + 搜索

`KnowledgeRawTab.tsx` 改造：

**布局**: 外层固定高度 `calc(100vh - 280px)`（最小 500px），左右两侧各自 `height:100%; overflowY:auto`。

**搜索**: 左侧顶部加搜索框，按 title/data_type 实时过滤。

```tsx
const [query, setQuery] = useState('')
const filtered = docs.filter(d =>
  d.title.toLowerCase().includes(query.toLowerCase()) ||
  d.data_type.toLowerCase().includes(query.toLowerCase())
)

<div style={{display:'flex', gap:16, height:'calc(100vh - 280px)', minHeight:500}}>
  <div style={{width:280, borderRight:'1px solid #e5e7eb', paddingRight:12, display:'flex', flexDirection:'column', minHeight:0}}>
    <h3>知识库文档 ({filtered.length}/{docs.length})</h3>
    <input placeholder="搜索文档..." value={query} onChange={e=>setQuery(e.target.value)}
      style={{marginBottom:8, padding:'6px 8px'}} />
    <div style={{flex:1, overflowY:'auto', minHeight:0}}>
      {filtered.map(d => <DocItem .../>)}
    </div>
  </div>
  <div style={{flex:1, overflow:'hidden', display:'flex', flexDirection:'column', minHeight:0}}>
    {/* Monaco 编辑器，height 100% */}
  </div>
</div>
```

### 3.7 Issue 7: 侧边栏折叠按钮显眼化

`Sidebar.tsx` `collapse-btn` 改造（保留 button 语义，视觉增强）：
- 尺寸 40×40（原 32×32 隐式）
- 背景 `var(--color-brand-100)`，hover 时 `var(--color-brand-200)`
- chevron 图标 22px（原 18px）
- 添加 `title` 属性 tooltip「收起菜单」/「展开菜单」
- 折叠态时按钮在侧边栏外缘浮动（更易点击）

### 3.8 Issue 8: 删除假消息铃铛

`Header.tsx` 删除：
- `Bell` 导入
- `unread = 3` 硬编码
- `header-notify` button 整段

### 3.9 Issue 9: 头像按钮 → 账号下拉菜单

`Header.tsx` `header-user` 改造：

```tsx
const [menuOpen, setMenuOpen] = useState(false)
const menuRef = useRef<HTMLDivElement>(null)
const { brand } = useBrandConfig()
const logout = useAuthStore(s => s.logout)
const navigate = useNavigate()

useEffect(() => {
  function onClickOutside(e: MouseEvent) {
    if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
      setMenuOpen(false)
    }
  }
  document.addEventListener('mousedown', onClickOutside)
  return () => document.removeEventListener('mousedown', onClickOutside)
}, [])

<div ref={menuRef} style={{position:'relative'}}>
  <button className="header-user" onClick={()=>setMenuOpen(v=>!v)}>
    <div className="avatar">{user?.username?.[0] || '管'}</div>
    <span className="uname">{user?.username || '管理员'}</span>
    <svg className="chevron" .../>
  </button>
  {menuOpen && (
    <div style={{
      position:'absolute', right:0, top:'100%', marginTop:8,
      minWidth:220, background:'#fff', border:'1px solid #e5e7eb',
      borderRadius:8, boxShadow:'0 4px 12px rgba(0,0,0,0.1)', zIndex:1000,
    }}>
      <div style={{padding:'12px 16px', borderBottom:'1px solid #f3f4f6'}}>
        <div style={{fontSize:12, color:'#888'}}>院校</div>
        <div style={{fontSize:13, fontWeight:600}}>{brand?.name || '招生智脑'}</div>
        <div style={{fontSize:12, color:'#888', marginTop:8}}>账号</div>
        <div style={{fontSize:13, fontWeight:600}}>{user?.username || 'admin'}</div>
        <div style={{fontSize:12, color:'#888', marginTop:8}}>角色</div>
        <div style={{fontSize:13, fontWeight:600}}>
          {user?.is_developer ? '开发者' : '院校管理员'}
        </div>
      </div>
      <button onClick={()=>{ logout(); navigate('/login') }}
        style={{width:'100%', padding:'10px 16px', textAlign:'left',
          background:'none', border:'none', cursor:'pointer', fontSize:13,
          color:'var(--color-danger)'}}>
        退出登录
      </button>
    </div>
  )}
</div>
```

移动端保留现有的「管理员」文字 span（不下拉）。

### 3.10 Issue 10: 关闭体验入口 + 注册 scnu 账号

#### 3.10.1 前端 LoginPage.tsx

删除：
- `loginDemo` 引用
- 「🚀 体验模式 · 跳过登录」按钮
- 「或」分隔线
- 提示文字

#### 3.10.2 前端 authStore.ts

删除 `loginDemo` 方法（连同 try/catch 内的假 token 降级逻辑）。

#### 3.10.3 后端 startup_seed.py

在现有 admin 用户创建后新增 scnu 用户：
```python
# 在 admin user 创建后
result = await db.execute(select(User).where(User.username == "scnu"))
scnu_user = result.scalar_one_or_none()

if not scnu_user:
    salt = os.urandom(16).hex()
    scnu_pwd_hash = salt + ":" + hashlib.sha256(
        (salt + "2026scnu").encode()
    ).hexdigest()
    scnu_user = User(
        username="scnu",
        password_hash=scnu_pwd_hash,
    )
    db.add(scnu_user)

result = await db.execute(
    select(TenantUser).where(
        TenantUser.tenant_id == tenant.id,
        TenantUser.user_id == scnu_user.id,
    )
)
scnu_link = result.scalar_one_or_none()
if not scnu_link:
    db.add(TenantUser(
        tenant_id=tenant.id,
        user_id=scnu_user.id,
        role="admin",  # 院校管理员（非开发者）
    ))
```

#### 3.10.4 权限区分（已通过现有机制实现）

| 账号 | 密码 | is_developer | 可见菜单 | /db 访问 |
|---|---|---|---|---|
| admin | admin123 | true | 全部（含数据库管理） | 允许 |
| scnu | 2026scnu | false | 不含数据库管理 | 重定向到 /dashboard |

依据：
- `auth_service.py:27` `is_developer = username == settings.dev_admin_username`（settings.dev_admin_username 默认 "admin"）
- `RequireDeveloper.tsx` 守卫 /db 路由
- `Sidebar.tsx:82-91` 数据库管理菜单仅 isDeveloper 可见

## 4. 验收标准

1. **I1**: 工作台「查看全部 →」可跳转到 /consultations
2. **I2**: 侧边栏菜单 + 工作台 Hero 标题均为「咨询管理」
3. **I3**: 重新生成摘要：按钮显示「重新生成中...」+ disabled；完成后绿色 toast「摘要已重新生成」；失败红色 toast
4. **I4**: AI 对话配置为 4 字段表单；保存后用 scnu 账号在咨询模块和推荐模块对话，AI 回答使用新名称/开场白/风格
5. **I5**: 提示词模板 tab 左侧 5 项列表，右侧编辑器，切换无需滚轮
6. **I6**: 知识库 Raw 左右独立滚动；左侧搜索框实时过滤；点击下方文档右侧编辑器内容同步且可见
7. **I7**: 侧边栏折叠按钮 hover 有明显背景变化，尺寸更大
8. **I8**: Header 无铃铛按钮
9. **I9**: Header 头像点击弹出下拉菜单，显示院校+账号+角色，可退出登录
10. **I10**: 登录页无体验入口；scnu/2026scnu 可登录且无数据库管理菜单；admin/admin123 可登录且有数据库管理菜单；scnu 账号访问 /db 重定向到 /dashboard

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| I4 向后兼容：现有 tenant 的 ai_persona.custom_prompt 丢失导致 AI 无 system prompt | `build_persona_prompt` 检测 custom_prompt 存在时降级使用旧值 |
| I4 咨询模块接入 persona 后影响现有回答质量 | persona_greeting 只 prepend 不修改原模板；测试用例覆盖空 persona 场景 |
| I10 scnu 账号已存在但密码不同 | startup_seed 幂等：仅在 user 不存在时创建，已存在不覆盖密码 |
| I9 下拉菜单在移动端布局错乱 | 移动端保留原文字 span，不下拉 |

## 6. 测试要求

- I3: 新增 `ConsultationsPage` 重新生成交互的单测（mock api，验证 loading 态与 toast）
- I4: 新增 `persona_service` 单测（build_persona_greeting / apply_persona_style / has_legacy_custom_prompt）
- I4: 新增 consult.py 集成测试，验证 persona_greeting 被注入到 system_content 前
- I4: 现有 chat.py 测试更新，验证新分支
- I10: 新增 startup_seed 测试，验证 scnu 用户被创建且 is_developer=false

## 7. 不在本次范围

- AI 对话配置的更多字段（如禁用词、回答长度限制等）
- 提示词模板的版本对比/diff 视图
- 知识库 Raw 的批量操作
- 通知系统真实实现（铃铛已删除，未来如需可重做）

## 8. 涉及文件汇总

| 文件 | 改动 |
|---|---|
| admin-spa/src/pages/DashboardPage.tsx | I1, I2 |
| admin-spa/src/components/Sidebar.tsx | I2, I7 |
| admin-spa/src/pages/ConsultationsPage.tsx | I3 |
| admin-spa/src/pages/AgentSettingsPage.tsx | I4, I5 |
| admin-spa/src/types/index.ts | I4 |
| admin-spa/src/components/db/KnowledgeRawTab.tsx | I6 |
| admin-spa/src/components/Header.tsx | I8, I9 |
| admin-spa/src/pages/LoginPage.tsx | I10 |
| admin-spa/src/stores/authStore.ts | I10 |
| backend/api/routes/chat.py | I4 |
| backend/api/routes/consult.py | I4 |
| backend/services/persona_service.py | I4 (新文件) |
| backend/core/startup_seed.py | I10 |
