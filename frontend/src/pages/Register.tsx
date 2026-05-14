import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function Register() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const register = useAuthStore((s) => s.register)
  const nav = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await register(username, password, '', 0, '')
      nav('/chat')
    } catch {
      setError('注册失败，请重试')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-xl shadow-sm border border-border w-full max-w-sm">
        <h2 className="text-2xl font-bold text-text mb-6 text-center">注册</h2>
        {error && <div className="bg-red-50 text-danger text-sm p-3 rounded-lg mb-4">{error}</div>}
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-3 focus:outline-none focus:ring-2 focus:ring-primary" placeholder="用户名" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <input className="w-full px-4 py-3 border border-border rounded-lg mb-6 focus:outline-none focus:ring-2 focus:ring-primary" type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button type="submit" className="w-full py-3 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition">注册</button>
        <p className="text-center text-muted text-sm mt-4">已有账号？<Link to="/login" className="text-primary hover:underline">登录</Link></p>
      </form>
    </div>
  )
}
