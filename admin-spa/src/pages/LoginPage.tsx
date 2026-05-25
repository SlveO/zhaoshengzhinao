import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import api from '../api/client'
import type { BrandConfig } from '../types'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [brand, setBrand] = useState<BrandConfig | null>(null)
  const login = useAuthStore((s) => s.login)
  const loginDemo = useAuthStore((s) => s.loginDemo)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const tenantSlug = searchParams.get('tenant') || localStorage.getItem('tenantSlug') || 'scnu'

  const handleDemo = () => {
    const slug = tenantSlug || 'demo'
    loginDemo(slug)
    navigate('/', { replace: true })
  }

  useEffect(() => {
    if (tenantSlug) {
      api.get<BrandConfig>('/admin/brand-config')
        .then((r) => setBrand(r.data))
        .catch(() => {})
    }
  }, [tenantSlug])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!username || !password || !tenantSlug) {
      setError('请输入用户名和密码')
      return
    }
    setLoading(true)
    setError('')
    try {
      await login(username, password, tenantSlug)
      navigate('/', { replace: true })
    } catch {
      setError('登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  const brandName = brand?.name || '招生智脑'
  const brandLogo = brand?.logo_url

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: brand?.login_bg_url ? `url(${brand.login_bg_url}) center/cover` : 'var(--color-page)',
    }}>
      <div className="login-container">
        <div className="login-brand-panel">
          {brandLogo ? (
            <img src={brandLogo} alt="" style={{
              width: 80, height: 80, borderRadius: 20, objectFit: 'cover',
              marginBottom: 22, border: '1px solid rgba(255,255,255,0.1)',
            }} />
          ) : (
            <div className="login-brand-logo">{brandName[0]}</div>
          )}
          <div className="login-brand-name">{brandName}</div>
          <div className="login-brand-subtitle">院校管理后台</div>
        </div>

        <div className="login-form-panel">
          <h2>登录管理后台</h2>
          <p className="hint">使用院校分配的账号登录</p>

          {tenantSlug && (
            <div className="login-tenant-badge">
              <span className="dot" />
              <span>院校标识：{tenantSlug.toUpperCase()}</span>
            </div>
          )}

          {!tenantSlug && (
            <div className="field">
              <label>院校标识</label>
              <input
                type="text" placeholder="如 scnu"
                onChange={(e) => localStorage.setItem('tenantSlug', e.target.value)}
              />
            </div>
          )}

          {error && <div className="login-error-msg">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>用户名</label>
              <input
                type="text" value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名" autoComplete="username" autoFocus
              />
            </div>
            <div className="field">
              <label>密码</label>
              <input
                type="password" value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码" autoComplete="current-password"
              />
            </div>
            <button type="submit" className="login-btn" disabled={loading} style={{ marginTop: 8 }}>
              {loading ? '登录中…' : '登 录'}
            </button>

            <div style={{
              display: 'flex', alignItems: 'center', gap: 10, marginTop: 16,
            }}>
              <div style={{ flex: 1, height: 1, background: 'var(--color-border)' }} />
              <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>或</span>
              <div style={{ flex: 1, height: 1, background: 'var(--color-border)' }} />
            </div>

            <button
              type="button"
              onClick={handleDemo}
              style={{
                width: '100%', marginTop: 12, padding: '11px 0',
                background: 'transparent', color: 'var(--color-brand-800)',
                border: '2px dashed var(--color-brand-300)', borderRadius: 8,
                fontSize: 14, fontWeight: 600, fontFamily: 'inherit',
                cursor: 'pointer', letterSpacing: '-0.01em',
                transition: 'all 0.15s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--color-brand-100)'
                e.currentTarget.style.borderColor = 'var(--color-brand-800)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent'
                e.currentTarget.style.borderColor = 'var(--color-brand-300)'
              }}
            >
              🚀 体验模式 · 跳过登录
            </button>
            <p style={{ fontSize: 11, color: 'var(--color-text-muted)', textAlign: 'center', marginTop: 6 }}>
              无需账号，直接进入管理后台查看完整功能演示
            </p>
          </form>
        </div>
      </div>
    </div>
  )
}
