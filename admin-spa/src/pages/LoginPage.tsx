import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const tenantSlug = searchParams.get('tenant') || localStorage.getItem('tenantSlug') || ''

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

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
      <div className="login-container">
        <div className="login-brand-panel">
          <div className="login-brand-logo">智</div>
          <div className="login-brand-name">招生智脑</div>
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
                type="text"
                placeholder="如 scnu"
                onChange={(e) => localStorage.setItem('tenantSlug', e.target.value)}
              />
            </div>
          )}

          {error && <div className="login-error-msg">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                autoComplete="username"
                autoFocus
              />
            </div>

            <div className="field">
              <label>密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                autoComplete="current-password"
              />
            </div>

            <button type="submit" className="login-btn" disabled={loading} style={{ marginTop: 8 }}>
              {loading ? '登录中…' : '登 录'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
