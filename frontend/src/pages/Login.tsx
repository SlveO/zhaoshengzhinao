import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const login = useAuthStore((s) => s.login)
  const nav = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try { await login(username, password); nav('/chat') }
    catch { setError('用户名或密码错误') }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm border border-border w-full max-w-sm">
        <h2 className="text-2xl font-bold text-text mb-6 text-center">登录</h2>
        {error && <div className="bg-red-50 text-danger text-sm p-3 rounded-lg mb-4">{error}</div>}
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-primary" placeholder="用户名" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-6 focus:outline-none focus:ring-2 focus:ring-primary" type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button type="submit" className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition">登录</button>
        <p className="text-center text-muted text-sm mt-4">还没有账号？<Link to="/register" className="text-primary hover:underline">注册</Link></p>
      </form>
    </div>
  )
}
