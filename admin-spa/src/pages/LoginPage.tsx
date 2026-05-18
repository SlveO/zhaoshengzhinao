import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [tenant, setTenant] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const prefilledTenant = searchParams.get('tenant') || localStorage.getItem('tenantSlug') || ''
  const displayTenant = tenant || prefilledTenant

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const slug = displayTenant
    if (!username || !password || !slug) {
      setError('请填写所有字段')
      return
    }
    setLoading(true)
    setError('')
    try {
      await login(username, password, slug)
      navigate('/', { replace: true })
    } catch {
      setError('登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white login-card w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-xl bg-gray-100 bg-center bg-contain bg-no-repeat"
            style={{ backgroundImage: 'var(--brand-logo)' }}
          />
          <h1 className="text-2xl font-bold text-gray-800">招生智脑</h1>
          <p className="text-gray-400 text-sm mt-1">院校管理后台</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {!prefilledTenant && (
            <div>
              <label className="block text-sm text-gray-600 mb-1">院校标识</label>
              <input
                type="text"
                value={tenant}
                onChange={(e) => setTenant(e.target.value)}
                placeholder="如 gdufs"
                className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)] focus:border-transparent transition"
              />
            </div>
          )}
          {prefilledTenant && (
            <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg text-sm text-gray-500">
              <span>院校：</span>
              <span className="font-medium text-gray-700">{prefilledTenant}</span>
            </div>
          )}

          <div>
            <label className="block text-sm text-gray-600 mb-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)] focus:border-transparent transition"
            />
          </div>

          <div>
            <label className="block text-sm text-gray-600 mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)] focus:border-transparent transition"
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm bg-red-50 px-3 py-2 rounded-lg">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg text-white font-medium text-sm transition cursor-pointer disabled:opacity-60"
            style={{ background: 'var(--brand-primary)' }}
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
      </div>
    </div>
  )
}
