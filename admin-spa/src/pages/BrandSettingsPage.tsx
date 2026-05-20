import { useEffect, useState, type FormEvent } from 'react'
import api from '../api/client'
import type { BrandConfig } from '../types'
import StatusCard from '../components/StatusCard'

const DEFAULTS: BrandConfig = {
  name: '华南师范大学',
  short_name: 'SCNU',
  primary_color: '#2563eb',
  secondary_color: '#f59e0b',
  logo_url: '',
  favicon_url: null,
  login_bg_url: null,
  welcome_text: '欢迎来到华南师范大学招生咨询平台！我是您的专属招生助手，为您解答关于专业选择、录取政策、校园生活等问题。',
}

export default function BrandSettingsPage() {
  const [brand, setBrand] = useState<BrandConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<BrandConfig>('/admin/brand-config')
      .then((r) => setBrand({ ...DEFAULTS, ...r.data }))
      .catch((e) => setError(e?.message || '获取品牌配置失败'))
  }, [])

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!brand) return
    setSaving(true)
    setMessage('')
    try {
      await api.put('/admin/brand-config', brand)
      setMessage('品牌配置已保存')
      document.title = `${brand.name} · 管理后台`
    } catch {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const reset = () => {
    setBrand({ ...DEFAULTS })
    setMessage('已恢复默认配置')
  }

  const update = (patch: Partial<BrandConfig>) => {
    if (!brand) return
    setBrand({ ...brand, ...patch })
  }

  return (
    <div>
      <StatusCard loading={!brand} error={error}>
        {brand && (
          <div className="chart-grid even">
            <div className="card">
              <div className="card-header"><h3>品牌配置</h3></div>
              <form onSubmit={handleSave}>
                <div className="form-grid">
                  <div className="field"><label>院校全称</label><input value={brand.name} onChange={(e) => update({ name: e.target.value })} /></div>
                  <div className="field"><label>院校简称</label><input value={brand.short_name} onChange={(e) => update({ short_name: e.target.value })} /></div>
                  <div className="field">
                    <label>主题色</label>
                    <div className="field-row">
                      <input type="color" value={brand.primary_color} onChange={(e) => update({ primary_color: e.target.value })} />
                      <input value={brand.primary_color} onChange={(e) => update({ primary_color: e.target.value })} style={{ flex: 1 }} />
                    </div>
                  </div>
                  <div className="field">
                    <label>辅助色</label>
                    <div className="field-row">
                      <input type="color" value={brand.secondary_color} onChange={(e) => update({ secondary_color: e.target.value })} />
                      <input value={brand.secondary_color} onChange={(e) => update({ secondary_color: e.target.value })} style={{ flex: 1 }} />
                    </div>
                  </div>
                  <div className="field"><label>Logo URL</label><input value={brand.logo_url} onChange={(e) => update({ logo_url: e.target.value })} placeholder="https://..." /></div>
                  <div className="field"><label>Favicon URL</label><input value={brand.favicon_url || ''} onChange={(e) => update({ favicon_url: e.target.value })} placeholder="https://..." /></div>
                  <div className="field"><label>登录背景图 URL</label><input value={brand.login_bg_url || ''} onChange={(e) => update({ login_bg_url: e.target.value })} placeholder="https://..." /></div>
                  <div className="field" style={{ gridColumn: '1 / -1' }}><label>欢迎语</label><textarea value={brand.welcome_text || ''} onChange={(e) => update({ welcome_text: e.target.value })} /></div>
                </div>
                <div className="btn-group" style={{ marginTop: 20 }}>
                  <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? '保存中...' : '保存配置'}</button>
                  <button type="button" className="btn btn-secondary" onClick={reset}>恢复默认</button>
                </div>
              </form>
            </div>

            <div className="card">
              <div className="card-header"><h3>实时预览</h3></div>
              <div className="brand-preview-box">
                <div className="brand-preview-logo" style={{ background: brand.primary_color }}>{brand.short_name[0]}</div>
                <div style={{ fontSize: 16, fontWeight: 600 }}>{brand.name}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{brand.short_name}</div>
                <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 12 }}>
                  <span className="brand-preview-swatch" style={{ background: brand.primary_color }} />
                  <span className="brand-preview-swatch" style={{ background: brand.secondary_color }} />
                </div>
              </div>
            </div>
          </div>
        )}

        {message && (
          <div className={`view-status loading`} style={{ marginTop: 16 }}>
            {message}
          </div>
        )}
      </StatusCard>
    </div>
  )
}
