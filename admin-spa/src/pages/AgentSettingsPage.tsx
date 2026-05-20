import { useEffect, useState, type FormEvent } from 'react'
import api from '../api/client'
import type { PersonaConfig } from '../types'
import StatusCard from '../components/StatusCard'

const DEFAULT_PERSONA: PersonaConfig = {
  custom_prompt: '你是一位专业、热情的招生咨询助手，代表{tenant_name}招生办。请根据学生的{stage}阶段和以下信息提供帮助：{slots_summary}。保持{style}的语气，帮助学生了解学校的优势和特色。',
  style: 'casual',
  proactive_recommend: true,
}

export default function AgentSettingsPage() {
  const [persona, setPersona] = useState<PersonaConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState('')

  useEffect(() => {
    api.get<PersonaConfig>('/admin/ai-persona')
      .then((r) => {
        const p = { ...DEFAULT_PERSONA, ...r.data }
        setPersona(p)
        setPreview(renderPrompt(p))
      })
      .catch((e) => setError(e?.message || '获取 AI 设置失败'))
  }, [])

  const renderPrompt = (p: PersonaConfig) => {
    const styleText = p.style === 'casual' ? '亲切自然的语气' : '正式专业的语气'
    return (p.custom_prompt || DEFAULT_PERSONA.custom_prompt)
      .replace(/\{tenant_name\}/g, '华南师范大学')
      .replace(/\{stage\}/g, '深度咨询阶段')
      .replace(/\{slots_summary\}/g, '已了解：省份=广东，选科=物化生，预估分数=620，意向专业=计算机/电子信息')
      .replace(/\{style\}/g, styleText)
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

  return (
    <div>
      <StatusCard loading={!persona} error={error}>
        {persona && (
          <div className="chart-grid even">
            <div className="card">
              <div className="card-header"><h3>AI 对话配置</h3></div>
              <form onSubmit={handleSave}>
                <div className="field">
                  <label>自定义提示词</label>
                  <textarea
                    value={persona.custom_prompt}
                    onChange={(e) => updatePersona({ custom_prompt: e.target.value })}
                    style={{ minHeight: 180 }}
                  />
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 16 }}>
                  可用占位符：<code>{'{stage}'}</code> <code>{'{slots_summary}'}</code> <code>{'{tenant_name}'}</code> <code>{'{style}'}</code>
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
              <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius)', padding: 14, fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--fg)' }}>
                {preview}
              </div>
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
