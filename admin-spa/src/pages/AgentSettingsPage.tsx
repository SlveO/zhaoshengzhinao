import { useEffect, useState, type FormEvent } from 'react'
import api from '../api/client'
import type { PersonaConfig } from '../types'

const DEFAULT_PERSONA: PersonaConfig = {
  custom_prompt: '',
  style: 'casual',
  proactive_recommend: true,
}

export default function AgentSettingsPage() {
  const [persona, setPersona] = useState<PersonaConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.get<PersonaConfig>('/admin/ai-persona').then((r) => {
      setPersona({ ...DEFAULT_PERSONA, ...r.data })
    })
  }, [])

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!persona) return
    setSaving(true)
    setMessage('')
    try {
      await api.put('/admin/ai-persona', persona)
      setMessage('保存成功')
    } catch {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (!persona) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        加载中...
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-gray-800">AI 对话设置</h2>
        <p className="text-sm text-gray-400 mt-1">
          自定义 AI 对话风格、提示词和交互行为
        </p>
      </div>

      <form onSubmit={handleSave} className="bg-white rounded-xl p-6 shadow-sm space-y-5">
        {/* Custom Prompt */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">
            自定义提示词
          </label>
          <textarea
            value={persona.custom_prompt}
            onChange={(e) => setPersona({ ...persona, custom_prompt: e.target.value })}
            rows={6}
            placeholder="输入自定义系统提示词，留空则使用默认提示词..."
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)] resize-y"
          />
          <p className="text-xs text-gray-400 mt-1">
            可用占位符：<code className="bg-gray-100 px-1 rounded">{'{stage}'}</code> — 当前对话阶段，{' '}
            <code className="bg-gray-100 px-1 rounded">{'{slots_summary}'}</code> — 学生画像摘要
          </p>
        </div>

        {/* Style Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-600 mb-1">对话风格</label>
          <div className="flex gap-3">
            {[
              { value: 'casual', label: '亲切', desc: '温暖、鼓励的语气' },
              { value: 'formal', label: '正式', desc: '专业、严谨的语气' },
            ].map((opt) => (
              <label
                key={opt.value}
                className={`flex-1 p-3 rounded-lg border-2 cursor-pointer transition ${
                  persona.style === opt.value
                    ? 'border-[var(--brand-primary)] bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="style"
                  value={opt.value}
                  checked={persona.style === opt.value}
                  onChange={(e) =>
                    setPersona({ ...persona, style: e.target.value as PersonaConfig['style'] })
                  }
                  className="sr-only"
                />
                <div className="text-sm font-medium text-gray-800">{opt.label}</div>
                <div className="text-xs text-gray-400 mt-0.5">{opt.desc}</div>
              </label>
            ))}
          </div>
        </div>

        {/* Proactive Recommend Toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div>
            <div className="text-sm font-medium text-gray-800">主动推荐</div>
            <div className="text-xs text-gray-400 mt-0.5">
              AI 在对话中适时主动推荐院校和专业
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={persona.proactive_recommend}
            onClick={() =>
              setPersona({ ...persona, proactive_recommend: !persona.proactive_recommend })
            }
            className={`relative w-11 h-6 rounded-full transition ${
              persona.proactive_recommend
                ? 'bg-[var(--brand-primary)]'
                : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition ${
                persona.proactive_recommend ? 'left-[22px]' : 'left-0.5'
              }`}
            />
          </button>
        </div>

        {/* Save Feedback */}
        {message && (
          <div
            className={`text-sm px-3 py-2 rounded-lg ${
              message.includes('成功') ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-500'
            }`}
          >
            {message}
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="px-6 py-2.5 rounded-lg text-white font-medium text-sm transition cursor-pointer disabled:opacity-60"
          style={{ background: 'var(--brand-primary)' }}
        >
          {saving ? '保存中...' : '保存'}
        </button>
      </form>
    </div>
  )
}
