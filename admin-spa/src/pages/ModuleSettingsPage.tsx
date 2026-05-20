import { useEffect, useState } from 'react'
import api from '../api/client'
import type { ModuleItem } from '../types'
import StatusCard from '../components/StatusCard'

const MODULE_DEFS: ModuleItem[] = [
  { key: 'funnel', name: '招生漏斗', desc: '分析从访问到报考的全链路转化', depends: [], enabled: true },
  { key: 'profile_dashboard', name: '画像看板', desc: '学生兴趣画像与价值观分布', depends: [], enabled: true },
  { key: 'topic_cloud', name: '增强分析', desc: '词云、情绪时间线、咨询热点', depends: [], enabled: true },
  { key: 'knowledge', name: '知识库', desc: '院校专属知识文档管理', depends: [], enabled: true },
  { key: 'brand', name: '品牌配置', desc: '院校品牌色、Logo、欢迎语', depends: [], enabled: true },
  { key: 'agent', name: 'AI 对话', desc: '智能体提示词、风格与主动推荐', depends: [], enabled: true },
  { key: 'recommendation', name: '专业推荐', desc: '基于画像的专业匹配推荐', depends: ['profile_dashboard'], enabled: true },
  { key: 'reports', name: '招生报告', desc: '招生优化报告生成中心', depends: ['funnel', 'topic_cloud'], enabled: true },
  { key: 'multi_department', name: '多院系管理', desc: '多院系数据分权管理', depends: ['knowledge'], enabled: false },
  { key: 'role_management', name: '角色权限', desc: '细粒度角色与权限控制', depends: ['multi_department'], enabled: false },
]

export default function ModuleSettingsPage() {
  const [modules, setModules] = useState<Record<string, boolean>>({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ modules?: Record<string, boolean> }>('/admin/tenants/me/config')
      .then((r) => {
        setModules(r.data?.modules || {})
      })
      .catch((e) => setError(e?.message || '获取配置失败'))
      .finally(() => setLoading(false))
  }, [])

  const toggle = (key: string) => {
    setModules((prev) => ({ ...prev, [key]: !prev[key] }))
    setMessage('')
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    try {
      await api.put('/admin/tenants/me/config', { modules })
      setMessage('模块配置已保存')
    } catch {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 18 }}>
        开启或关闭各功能模块。带有下游依赖的模块关闭前需先关闭依赖模块。
      </div>

      <StatusCard loading={loading} error={error}>
        <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {MODULE_DEFS.map((m) => {
            const enabled = modules[m.key] ?? m.enabled
            const hasDeps = m.depends.length > 0
            return (
              <div key={m.key} className="card module-card" style={{ opacity: enabled || !hasDeps ? 1 : 0.5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 8 }}>
                  <h3 style={{ fontSize: 14, margin: 0 }}>{m.name}</h3>
                  <button
                    className={`switch${enabled ? ' on' : ''}`}
                    onClick={() => toggle(m.key)}
                    disabled={!hasDeps || enabled ? false : true}
                  />
                </div>
                <p style={{ fontSize: 12, color: 'var(--muted)', margin: '0 0 8px' }}>{m.desc}</p>
                {hasDeps && (
                  <div style={{ fontSize: 11, color: 'var(--amber)' }}>
                    依赖：{m.depends.map((d) => MODULE_DEFS.find((x) => x.key === d)?.name || d).join('、')}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {message && (
          <div className="view-status loading" style={{ marginTop: 16 }}>
            {message}
          </div>
        )}

        <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存模块配置'}
        </button>
      </StatusCard>
    </div>
  )
}
