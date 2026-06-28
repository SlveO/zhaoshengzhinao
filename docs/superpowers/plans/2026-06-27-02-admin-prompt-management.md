# Admin-SPA 提示词管理实施计划 (Plan 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 admin-spa 中实现多提示词在线编辑界面：列出所有 prompt_key、查看/编辑当前 active 内容、保存触发后端 DB+代码双写、展示健康状态。

**Architecture:** 在现有 AgentSettingsPage.tsx 基础上重构为多 prompt 模式（保留原 ai-persona 配置作为独立 tab）。新增 promptAdmin API 模块、PromptEditor 通用组件、健康检查指示器。

**Tech Stack:** React 19、TypeScript、Vite、Zustand、axios。

**依赖：** Plan 1 已完成后端 `/api/v1/admin/prompts` 系列接口。

**参考设计文档：** `docs/superpowers/specs/2026-06-27-consult-module-design.md`

---

## 文件结构

新增文件：
- `admin-spa/src/api/prompts.ts` — 提示词 API 端点模块
- `admin-spa/src/types/prompt.ts` — Prompt DTO 类型
- `admin-spa/src/components/PromptEditor.tsx` — 单个提示词编辑器组件
- `admin-spa/src/components/PromptHealthBadge.tsx` — 健康状态徽章

修改文件：
- `admin-spa/src/pages/AgentSettingsPage.tsx` — 新增"提示词模板"tab
- `admin-spa/src/types/index.ts` — 导出新类型

---

## Task 1: 定义提示词类型

**Files:**
- Create: `admin-spa/src/types/prompt.ts`
- Modify: `admin-spa/src/types/index.ts` (若存在则追加 export，否则新建)

- [ ] **Step 1: 创建 prompt 类型定义**

Create `admin-spa/src/types/prompt.ts`:
```typescript
/** 提示词模板 DTO（与后端 /api/v1/admin/prompts 响应对齐） */

export interface PromptSummary {
  prompt_key: string
  content: string
  version: number | null
  source: 'db' | 'code_default'
}

export interface PromptDetail {
  prompt_key: string
  content: string
  version: number | null
}

export interface PromptSaveResponse {
  prompt_key: string
  version: number
  sync_triggered: boolean
}

export interface PromptHealthMismatch {
  prompt_key: string
  db_active: boolean
  diff_size: number
}

export interface PromptHealth {
  total_keys: number
  consistent: boolean
  mismatches: PromptHealthMismatch[]
}

/** prompt_key 中文标签映射（用于 UI 展示） */
export const PROMPT_KEY_LABELS: Record<string, string> = {
  consult_system: '咨询模块 - 系统提示词',
  consult_intent: '咨询模块 - 意图抽取',
  consult_degraded: '咨询模块 - 降级重生成',
}

/** 各 prompt_key 的简短描述（编辑器顶部说明） */
export const PROMPT_KEY_DESCRIPTIONS: Record<string, string> = {
  consult_system: '咨询模块主回答的 system prompt。控制回答风格、数据引用规则、输出格式。',
  consult_intent: '从用户消息抽取意图（intent_type/majors/province/year）的 prompt。返回 JSON。',
  consult_degraded: '校验失败后的降级重生成 prompt。强制逐条陈述数据表，禁止归纳。',
}
```

- [ ] **Step 2: 在 types/index.ts 中追加 export（若文件不存在则跳过）**

Run: `cd admin-spa && ls src/types/`
若存在 `index.ts`，追加：`export * from './prompt'`
若不存在，跳过此步骤（直接从 `./prompt` 导入即可）。

- [ ] **Step 3: 验证类型编译**

Run: `cd admin-spa && npx tsc --noEmit src/types/prompt.ts`
Expected: 无错误

- [ ] **Step 4: Commit**

```bash
cd admin-spa
git add src/types/prompt.ts
git commit -m "feat(admin-spa): add prompt type definitions"
```

---

## Task 2: 创建 prompts API 模块

**Files:**
- Create: `admin-spa/src/api/prompts.ts`

- [ ] **Step 1: 创建 prompts API 模块**

Create `admin-spa/src/api/prompts.ts`:
```typescript
import api from './client'
import type {
  PromptSummary,
  PromptDetail,
  PromptSaveResponse,
  PromptHealth,
} from '../types/prompt'

/** 统一响应包装（与后端 {data, error} 一致） */
interface ApiResponse<T> {
  data: T | null
  error: { code: string; message: string } | null
}

/** 列出所有 prompt_key 及当前 active 内容 */
export async function listPrompts(): Promise<PromptSummary[]> {
  const resp = await api.get<ApiResponse<{ items: PromptSummary[] }>>('/admin/prompts')
  if (resp.data.error) {
    throw new Error(resp.data.error.message)
  }
  return resp.data.data?.items ?? []
}

/** 获取单个 prompt 详情 */
export async function getPrompt(promptKey: string): Promise<PromptDetail> {
  const resp = await api.get<ApiResponse<PromptDetail>>(`/admin/prompts/${promptKey}`)
  if (resp.data.error) {
    throw new Error(resp.data.error.message)
  }
  return resp.data.data as PromptDetail
}

/** 保存新版本（触发后端 DB+代码双写） */
export async function savePrompt(
  promptKey: string,
  content: string,
  expectedVersion: number | null,
): Promise<PromptSaveResponse> {
  const resp = await api.post<ApiResponse<PromptSaveResponse>>(
    `/admin/prompts/${promptKey}`,
    { content, expected_version: expectedVersion },
  )
  if (resp.data.error) {
    throw new Error(resp.data.error.message)
  }
  return resp.data.data as PromptSaveResponse
}

/** 健康检查（DB↔代码一致性） */
export async function checkPromptHealth(): Promise<PromptHealth> {
  const resp = await api.get<ApiResponse<PromptHealth>>('/admin/prompts/health/check')
  if (resp.data.error) {
    throw new Error(resp.data.error.message)
  }
  return resp.data.data as PromptHealth
}
```

- [ ] **Step 2: 验证编译**

Run: `cd admin-spa && npx tsc --noEmit src/api/prompts.ts`
Expected: 无错误

- [ ] **Step 3: Commit**

```bash
cd admin-spa
git add src/api/prompts.ts
git commit -m "feat(admin-spa): add prompts API client"
```

---

## Task 3: 创建 PromptHealthBadge 组件

**Files:**
- Create: `admin-spa/src/components/PromptHealthBadge.tsx`

- [ ] **Step 1: 创建健康状态徽章组件**

Create `admin-spa/src/components/PromptHealthBadge.tsx`:
```typescript
import { useEffect, useState } from 'react'
import { checkPromptHealth } from '../api/prompts'
import type { PromptHealth } from '../types/prompt'

/**
 * 提示词 DB↔代码一致性健康徽章。
 * - consistent=true: 绿色"已同步"
 * - consistent=false: 黄色"X 项不一致"，点击展开详情
 * - 加载中: 灰色"检查中"
 * - 错误: 红色"检查失败"
 */
export default function PromptHealthBadge() {
  const [health, setHealth] = useState<PromptHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)

  const refresh = async () => {
    setLoading(true)
    setError(null)
    try {
      const h = await checkPromptHealth()
      setHealth(h)
    } catch (e: any) {
      setError(e?.message || '检查失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  if (loading) {
    return <span className="health-badge health-badge-loading">检查中...</span>
  }

  if (error) {
    return (
      <span className="health-badge health-badge-error" title={error}>
        检查失败
      </span>
    )
  }

  if (!health) return null

  if (health.consistent) {
    return (
      <span className="health-badge health-badge-ok">
        已同步 ({health.total_keys})
      </span>
    )
  }

  return (
    <span>
      <span
        className="health-badge health-badge-warn"
        onClick={() => setExpanded(!expanded)}
        style={{ cursor: 'pointer' }}
      >
        {health.mismatches.length} 项不一致 ▾
      </span>
      {expanded && (
        <div className="health-detail">
          {health.mismatches.map((m) => (
            <div key={m.prompt_key} className="health-detail-item">
              <code>{m.prompt_key}</code>
              <span>差异 {m.diff_size} 字符</span>
            </div>
          ))}
          <button onClick={refresh} className="health-refresh-btn">
            重新检查
          </button>
        </div>
      )}
    </span>
  )
}
```

- [ ] **Step 2: 在全局 CSS 中追加徽章样式**

Edit `admin-spa/src/index.css`（或全局样式文件），追加：
```css
.health-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.health-badge-loading { background: #E5E7EB; color: #6B7280; }
.health-badge-ok { background: #D1FAE5; color: #065F46; }
.health-badge-warn { background: #FEF3C7; color: #92400E; }
.health-badge-error { background: #FEE2E2; color: #991B1B; }
.health-detail {
  margin-top: 8px;
  padding: 12px;
  background: #FFFBEB;
  border: 1px solid #FCD34D;
  border-radius: 6px;
  font-size: 13px;
}
.health-detail-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}
.health-refresh-btn {
  margin-top: 8px;
  padding: 4px 12px;
  background: white;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  cursor: pointer;
}
```

- [ ] **Step 3: Commit**

```bash
cd admin-spa
git add src/components/PromptHealthBadge.tsx src/index.css
git commit -m "feat(admin-spa): add PromptHealthBadge component"
```

---

## Task 4: 创建 PromptEditor 组件

**Files:**
- Create: `admin-spa/src/components/PromptEditor.tsx`

- [ ] **Step 1: 创建单 prompt 编辑器组件**

Create `admin-spa/src/components/PromptEditor.tsx`:
```typescript
import { useEffect, useState } from 'react'
import { getPrompt, savePrompt } from '../api/prompts'
import { PROMPT_KEY_LABELS, PROMPT_KEY_DESCRIPTIONS } from '../types/prompt'

interface Props {
  promptKey: string
  /** 保存成功后回调，供父组件刷新列表 */
  onSaved?: (newVersion: number) => void
}

/**
 * 单个提示词编辑器。
 * - 加载时显示当前 active 内容
 * - 编辑后保存触发乐观锁检查（expected_version）
 * - 显示版本号、来源（DB/代码默认）
 * - 409 冲突时提示用户重新加载
 */
export default function PromptEditor({ promptKey, onSaved }: Props) {
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [version, setVersion] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'ok' | 'error'; text: string } | null>(null)

  const label = PROMPT_KEY_LABELS[promptKey] || promptKey
  const description = PROMPT_KEY_DESCRIPTIONS[promptKey] || ''
  const dirty = content !== originalContent

  const load = async () => {
    setLoading(true)
    try {
      const detail = await getPrompt(promptKey)
      setContent(detail.content)
      setOriginalContent(detail.content)
      setVersion(detail.version)
      setMessage(null)
    } catch (e: any) {
      setMessage({ type: 'error', text: e?.message || '加载失败' })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [promptKey])

  const handleSave = async () => {
    if (!dirty) return
    setSaving(true)
    setMessage(null)
    try {
      const resp = await savePrompt(promptKey, content, version)
      setVersion(resp.version)
      setOriginalContent(content)
      setMessage({ type: 'ok', text: `已保存 v${resp.version}（代码同步已触发）` })
      onSaved?.(resp.version)
    } catch (e: any) {
      const msg = e?.response?.data?.error?.message || e?.message || '保存失败'
      if (e?.response?.status === 409) {
        setMessage({ type: 'error', text: '版本冲突，请重新加载后再保存' })
      } else {
        setMessage({ type: 'error', text: msg })
      }
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setContent(originalContent)
    setMessage(null)
  }

  if (loading) {
    return <div className="prompt-editor-loading">加载中...</div>
  }

  return (
    <div className="prompt-editor">
      <div className="prompt-editor-header">
        <div>
          <h4 className="prompt-editor-title">{label}</h4>
          <p className="prompt-editor-desc">{description}</p>
        </div>
        <div className="prompt-editor-meta">
          <span className="prompt-version">
            {version ? `v${version} (DB)` : '代码默认值'}
          </span>
        </div>
      </div>

      <textarea
        className="prompt-editor-textarea"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={18}
        spellCheck={false}
        style={{ fontFamily: 'monospace', fontSize: 13 }}
      />

      <div className="prompt-editor-actions">
        <button
          onClick={handleSave}
          disabled={!dirty || saving}
          className="prompt-save-btn"
        >
          {saving ? '保存中...' : '保存新版本'}
        </button>
        <button
          onClick={handleReset}
          disabled={!dirty || saving}
          className="prompt-reset-btn"
        >
          撤销修改
        </button>
        <button
          onClick={load}
          disabled={saving}
          className="prompt-reload-btn"
        >
          重新加载
        </button>
        <span className="prompt-dirty-indicator">
          {dirty ? '● 未保存' : '○ 已同步'}
        </span>
      </div>

      {message && (
        <div className={`prompt-message prompt-message-${message.type}`}>
          {message.text}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 追加编辑器样式**

Edit `admin-spa/src/index.css`，追加：
```css
.prompt-editor {
  border: 1px solid #E5E7EB;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  background: white;
}
.prompt-editor-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}
.prompt-editor-title { margin: 0; font-size: 15px; font-weight: 600; }
.prompt-editor-desc { margin: 4px 0 0; font-size: 12px; color: #6B7280; }
.prompt-version {
  font-size: 12px;
  padding: 2px 8px;
  background: #F3F4F6;
  border-radius: 4px;
  color: #6B7280;
}
.prompt-editor-textarea {
  width: 100%;
  border: 1px solid #D1D5DB;
  border-radius: 6px;
  padding: 12px;
  resize: vertical;
  line-height: 1.6;
}
.prompt-editor-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
.prompt-save-btn {
  padding: 6px 16px;
  background: #1A56DB;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.prompt-save-btn:disabled { background: #9CA3AF; cursor: not-allowed; }
.prompt-reset-btn, .prompt-reload-btn {
  padding: 6px 12px;
  background: white;
  border: 1px solid #D1D5DB;
  border-radius: 4px;
  cursor: pointer;
}
.prompt-reset-btn:disabled, .prompt-reload-btn:disabled { cursor: not-allowed; opacity: 0.5; }
.prompt-dirty-indicator { font-size: 12px; color: #6B7280; margin-left: auto; }
.prompt-message { margin-top: 12px; padding: 8px 12px; border-radius: 4px; font-size: 13px; }
.prompt-message-ok { background: #D1FAE5; color: #065F46; }
.prompt-message-error { background: #FEE2E2; color: #991B1B; }
```

- [ ] **Step 3: Commit**

```bash
cd admin-spa
git add src/components/PromptEditor.tsx src/index.css
git commit -m "feat(admin-spa): add PromptEditor component"
```

---

## Task 5: 重构 AgentSettingsPage 集成提示词管理

**Files:**
- Modify: `admin-spa/src/pages/AgentSettingsPage.tsx`

- [ ] **Step 1: 在 AgentSettingsPage 顶部新增 tab 切换**

Edit `admin-spa/src/pages/AgentSettingsPage.tsx`，在文件顶部 import 后追加：
```typescript
import { useState } from 'react'
import PromptEditor from '../components/PromptEditor'
import PromptHealthBadge from '../components/PromptHealthBadge'
import { listPrompts } from '../api/prompts'
import type { PromptSummary } from '../types/prompt'

type SettingsTab = 'persona' | 'prompts'
```

并在组件函数体顶部追加：
```typescript
  const [activeTab, setActiveTab] = useState<SettingsTab>('persona')
  const [promptKeys, setPromptKeys] = useState<string[]>([])

  useEffect(() => {
    if (activeTab === 'prompts' && promptKeys.length === 0) {
      listPrompts()
        .then((items) => setPromptKeys(items.map((p) => p.prompt_key)))
        .catch((e) => console.error('Failed to load prompt list:', e))
    }
  }, [activeTab])
```

- [ ] **Step 2: 在 render 中添加 tab 切换 UI**

在 return 的最外层 div 内，原 StatusCard 之前追加 tab 切换：
```tsx
      <div className="settings-tabs">
        <button
          className={`settings-tab ${activeTab === 'persona' ? 'active' : ''}`}
          onClick={() => setActiveTab('persona')}
        >
          AI 对话配置
        </button>
        <button
          className={`settings-tab ${activeTab === 'prompts' ? 'active' : ''}`}
          onClick={() => setActiveTab('prompts')}
        >
          提示词模板
        </button>
        {activeTab === 'prompts' && <PromptHealthBadge />}
      </div>
```

- [ ] **Step 3: 条件渲染 persona 原内容 vs prompts 编辑器**

将原 `{persona && (...)}` 块包裹在 `{activeTab === 'persona' && (...)}` 内，然后追加 prompts tab 内容：
```tsx
      {activeTab === 'prompts' && (
        <div className="prompts-container">
          {promptKeys.length === 0 ? (
            <div className="prompts-loading">加载提示词列表...</div>
          ) : (
            promptKeys.map((key) => (
              <PromptEditor key={key} promptKey={key} />
            ))
          )}
        </div>
      )}
```

- [ ] **Step 4: 追加 tab 样式**

Edit `admin-spa/src/index.css`，追加：
```css
.settings-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid #E5E7EB;
  padding-bottom: 8px;
}
.settings-tab {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 14px;
  color: #6B7280;
}
.settings-tab.active {
  color: #1A56DB;
  border-bottom-color: #1A56DB;
  font-weight: 500;
}
.prompts-container { padding: 0 0 24px; }
.prompts-loading { padding: 24px; color: #6B7280; text-align: center; }
```

- [ ] **Step 5: 验证编译**

Run: `cd admin-spa && npx tsc --noEmit`
Expected: 无错误

- [ ] **Step 6: 启动 dev server 验证页面**

Run: `cd admin-spa && npm run dev`
打开浏览器 http://localhost:3001?tenant=scnu，登录后访问 AI 设置页面，验证：
1. 顶部出现两个 tab："AI 对话配置" / "提示词模板"
2. 切换到"提示词模板"显示 3 个编辑器（consult_system / consult_intent / consult_degraded）
3. 健康徽章显示"已同步 (3)"或"X 项不一致"

- [ ] **Step 7: Commit**

```bash
cd admin-spa
git add src/pages/AgentSettingsPage.tsx src/index.css
git commit -m "feat(admin-spa): integrate prompt management tab into AgentSettingsPage"
```

---

## Self-Review

**1. Spec coverage：**
- 在线编辑提示词 → Task 1-5 ✓
- 保存后触发 DB+代码同步 → 后端 Plan 1 Task 17 ✓
- 健康检查展示 → Task 3 + Task 5 ✓
- 多 prompt 切换 → Task 5（多 PromptEditor 实例）✓
- 不新增页面，集成到现有 AgentSettingsPage → Task 5 ✓

**2. Placeholder scan：** 无 TBD / TODO

**3. Type consistency：**
- `PromptSummary` / `PromptDetail` / `PromptSaveResponse` / `PromptHealth` 在 Task 1/2/3/4 一致
- API 路径 `/admin/prompts` 与 Plan 1 Task 17 一致

---

## Execution Handoff

Plan 2 已完成并保存至 `docs/superpowers/plans/2026-06-27-02-admin-prompt-management.md`。

**两种执行方式：**

**1. Subagent-Driven（推荐）** — 每个 Task 派发独立 sub-agent

**2. Inline Execution** — 当前会话内顺序执行

**请选择执行方式？**
