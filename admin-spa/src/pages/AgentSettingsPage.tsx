import { useEffect, useMemo, useState, type FormEvent } from 'react'
import api from '../api/client'
import type { PersonaConfig } from '../types'
import StatusCard from '../components/StatusCard'
import PromptEditor from '../components/PromptEditor'
import PromptHealthBadge from '../components/PromptHealthBadge'
import { listPrompts } from '../api/prompts'

type SettingsTab = 'persona' | 'prompts'

const DEFAULT_PERSONA: PersonaConfig = {
  assistant_name: '华小狮',
  greeting: '你好，我是华南师范大学招生助手，有什么可以帮你的吗？',
  style: 'casual',
  proactive_recommend: true,
}

const PROMPT_LABELS: Record<string, string> = {
  b2b_system: '推荐系统提示词',
  consult_system: '咨询系统提示词',
  consult_degraded: '咨询降级提示词',
  consult_intent: '咨询意图识别',
  consult_summary: '咨询摘要生成',
}

function promptLabel(key: string): string {
  return PROMPT_LABELS[key] || key
}

export default function AgentSettingsPage() {
  const [persona, setPersona] = useState<PersonaConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState('')
  const [activeTab, setActiveTab] = useState<SettingsTab>('persona')
  const [promptKeys, setPromptKeys] = useState<string[]>([])
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null)

  useEffect(() => {
    api.get<PersonaConfig>('/admin/ai-persona')
      .then((r) => {
        // 兼容老数据：仅在新字段缺失时填默认值，保留 custom_prompt 用于回退
        const merged: PersonaConfig = {
          ...DEFAULT_PERSONA,
          ...r.data,
          assistant_name: r.data?.assistant_name || DEFAULT_PERSONA.assistant_name,
          greeting: r.data?.greeting || DEFAULT_PERSONA.greeting,
          style: r.data?.style || DEFAULT_PERSONA.style,
          proactive_recommend:
            r.data?.proactive_recommend ?? DEFAULT_PERSONA.proactive_recommend,
        }
        setPersona(merged)
        setPreview(renderPrompt(merged))
      })
      .catch((e) => setError(e?.message || '获取 AI 设置失败'))
  }, [])

  useEffect(() => {
    if (activeTab === 'prompts' && promptKeys.length === 0) {
      listPrompts()
        .then((items) => {
          const keys = items.map((p) => p.prompt_key)
          setPromptKeys(keys)
          if (keys.length > 0 && selectedPrompt === null) {
            setSelectedPrompt(keys[0])
          }
        })
        .catch((e) => console.error('Failed to load prompt list:', e))
    }
  }, [activeTab])

  const renderPrompt = (p: PersonaConfig) => {
    const styleText = p.style === 'casual' ? '亲切自然' : '正式专业'
    const lines = [
      `【AI 助手形象预览】`,
      `助手名称：${p.assistant_name}`,
      `对话风格：${styleText}`,
      ``,
      `开场白：`,
      p.greeting,
      ``,
      `主动推荐：${p.proactive_recommend ? '已开启 — AI 会主动推荐匹配专业' : '已关闭'}`,
    ]
    return lines.join('\n')
  }

  const updatePersona = (patch: Partial<PersonaConfig>) => {
    if (!persona) return
    const p = { ...persona, ...patch }
    setPersona(p)
    setPreview(renderPrompt(p))
  }

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!persona) return
    setSaving(true)
    setMessage('')
    try {
      await api.put('/admin/ai-persona', persona)
      setMessage('AI 配置已保存')
    } catch {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const sortedPromptKeys = useMemo(
    () => [...promptKeys].sort((a, b) => promptLabel(a).localeCompare(promptLabel(b), 'zh-CN')),
    [promptKeys],
  )

  return (
    <div>
      <StatusCard loading={!persona} error={error}>
        <div className="settings-tabs">
          <button
            className={`settings-tab${activeTab === 'persona' ? ' active' : ''}`}
            onClick={() => setActiveTab('persona')}
          >
            AI 对话配置
          </button>
          <button
            className={`settings-tab${activeTab === 'prompts' ? ' active' : ''}`}
            onClick={() => setActiveTab('prompts')}
          >
            提示词模板
          </button>
          {activeTab === 'prompts' && <PromptHealthBadge />}
        </div>

        {activeTab === 'persona' && persona && (
          <div className="chart-grid even">
            <div className="card">
              <div className="card-header"><h3>AI 对话形象配置</h3></div>
              <form onSubmit={handleSave}>
                <div className="field">
                  <label>助手名称 <span style={{ color: 'var(--muted)', fontSize: 11 }}>（学生侧显示的 AI 称呼）</span></label>
                  <input
                    type="text"
                    value={persona.assistant_name}
                    onChange={(e) => updatePersona({ assistant_name: e.target.value })}
                    placeholder="如：华小狮、华师招生助手"
                    style={{ width: '100%' }}
                  />
                </div>

                <div className="field">
                  <label>开场白 / 自我介绍 <span style={{ color: 'var(--muted)', fontSize: 11 }}>（学生进入会话时看到的第一句话）</span></label>
                  <textarea
                    value={persona.greeting}
                    onChange={(e) => updatePersona({ greeting: e.target.value })}
                    style={{ minHeight: 80 }}
                    placeholder="如：你好，我是华南师范大学招生助手，有什么可以帮你的吗？"
                  />
                </div>

                <div className="field">
                  <label>对话风格</label>
                  <div className="radio-cards">
                    <div
                      className={`radio-card${persona.style === 'casual' ? ' selected' : ''}`}
                      onClick={() => updatePersona({ style: 'casual' })}
                    >
                      亲切自然<br /><small style={{ color: 'var(--muted)', fontSize: 11 }}>如学长般温和交流</small>
                    </div>
                    <div
                      className={`radio-card${persona.style === 'formal' ? ' selected' : ''}`}
                      onClick={() => updatePersona({ style: 'formal' })}
                    >
                      正式专业<br /><small style={{ color: 'var(--muted)', fontSize: 11 }}>如招生官般严谨</small>
                    </div>
                  </div>
                </div>

                <div className="field">
                  <label>主动推荐</label>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <button
                      type="button"
                      className={`switch${persona.proactive_recommend ? ' on' : ''}`}
                      onClick={() => updatePersona({ proactive_recommend: !persona.proactive_recommend })}
                    />
                    <span style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {persona.proactive_recommend ? '已开启 — AI 会主动推荐匹配专业' : '已关闭 — AI 仅在用户询问时推荐'}
                    </span>
                  </div>
                </div>

                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? '保存中...' : '保存配置'}
                </button>
              </form>
            </div>

            <div className="card">
              <div className="card-header"><h3>提示词渲染预览</h3><span className="badge">示例数据</span></div>
              <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius)', padding: 14, fontSize: 13, lineHeight: 1.7, whiteSpace: 'pre-wrap', color: 'var(--fg)' }}>
                {preview}
              </div>
              <div style={{ marginTop: 12, fontSize: 11, color: 'var(--muted)', lineHeight: 1.6 }}>
                <strong>说明：</strong>该形象配置会同时被「咨询模块」（学生咨询问答）和「个性化推荐模块」（一对一推荐会话）调用，确保学生侧体验一致。
              </div>
            </div>
          </div>
        )}

        {activeTab === 'prompts' && (
          <div style={{ display: 'flex', gap: 16, minHeight: 560, alignItems: 'stretch' }}>
            <div
              className="card"
              style={{ width: 240, flexShrink: 0, padding: 0, display: 'flex', flexDirection: 'column' }}
            >
              <div className="card-header" style={{ padding: '12px 14px', borderBottom: '1px solid var(--border)' }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>提示词列表</h3>
              </div>
              <div style={{ overflowY: 'auto', flex: 1, padding: '6px 0' }}>
                {sortedPromptKeys.length === 0 ? (
                  <div style={{ padding: 14, fontSize: 12, color: 'var(--muted)' }}>加载中...</div>
                ) : (
                  sortedPromptKeys.map((key) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setSelectedPrompt(key)}
                      style={{
                        display: 'block',
                        width: '100%',
                        textAlign: 'left',
                        padding: '10px 14px',
                        background: selectedPrompt === key ? 'var(--accent-bg, #eff6ff)' : 'transparent',
                        border: 'none',
                        borderLeft: selectedPrompt === key ? '3px solid var(--primary, #2563eb)' : '3px solid transparent',
                        cursor: 'pointer',
                        fontSize: 13,
                        color: selectedPrompt === key ? 'var(--primary, #2563eb)' : 'var(--fg)',
                        fontWeight: selectedPrompt === key ? 600 : 400,
                      }}
                    >
                      {promptLabel(key)}
                    </button>
                  ))
                )}
              </div>
            </div>

            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
              {selectedPrompt ? (
                <PromptEditor key={selectedPrompt} promptKey={selectedPrompt} />
              ) : (
                <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 13 }}>
                  请在左侧选择一个提示词进行编辑
                </div>
              )}
            </div>
          </div>
        )}

        {message && (
          <div className="view-status loading" style={{ marginTop: 16 }}>
            {message}
          </div>
        )}
      </StatusCard>
    </div>
  )
}
