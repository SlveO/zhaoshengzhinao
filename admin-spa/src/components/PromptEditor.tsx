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
 * - 编辑后保存触发后端 DB+代码双写
 * - 显示版本号、是否已定制（DB vs 代码默认）
 * - 提供"恢复代码默认值"快捷操作
 */
export default function PromptEditor({ promptKey, onSaved }: Props) {
  const [content, setContent] = useState('')
  const [originalContent, setOriginalContent] = useState('')
  const [codeDefault, setCodeDefault] = useState('')
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
      setCodeDefault(detail.code_default)
      setVersion(detail.active_version)
      setMessage(null)
    } catch (e) {
      setMessage({ type: 'error', text: e instanceof Error ? e.message : '加载失败' })
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
      const resp = await savePrompt(promptKey, content)
      setVersion(resp.version)
      setOriginalContent(content)
      const syncNote = resp.sync_success ? '代码同步已触发' : '代码同步失败（DB 已更新）'
      setMessage({ type: 'ok', text: `已保存 v${resp.version}（${syncNote}）` })
      onSaved?.(resp.version)
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      const msg = err?.response?.data?.detail || err?.message || '保存失败'
      setMessage({ type: 'error', text: msg })
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setContent(originalContent)
    setMessage(null)
  }

  const handleRestoreDefault = () => {
    setContent(codeDefault)
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
          onClick={handleRestoreDefault}
          disabled={saving || content === codeDefault}
          className="prompt-reload-btn"
          title="恢复为代码默认值（仍需点击保存）"
        >
          恢复默认值
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
