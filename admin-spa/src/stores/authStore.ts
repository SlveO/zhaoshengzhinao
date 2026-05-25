import { create } from 'zustand'
import api from '../api/client'
import type { LoginResponse } from '../types'

interface AuthState {
  token: string | null
  user: { id: string; username: string } | null
  role: 'demo' | 'admin'
  login: (username: string, password: string, tenantSlug: string) => Promise<void>
  loginDemo: (tenantSlug: string) => void
  logout: () => void
  setRole: (role: 'demo' | 'admin') => void
}

const DEMO_TOKEN = 'demo-token-netlify-preview'

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  role: (localStorage.getItem('role') as 'demo' | 'admin') || 'demo',

  login: async (username: string, password: string, tenantSlug: string) => {
    localStorage.setItem('tenantSlug', tenantSlug)
    const res = await api.post<LoginResponse>('/auth/login', { username, password })
    const { access_token, user_id, username: uname } = res.data
    localStorage.setItem('token', access_token)
    localStorage.setItem('role', 'admin')
    localStorage.setItem('user', JSON.stringify({ id: user_id, username: uname }))
    set({ token: access_token, role: 'admin', user: { id: user_id, username: uname } })
  },

  loginDemo: (tenantSlug: string) => {
    localStorage.setItem('tenantSlug', tenantSlug)
    localStorage.setItem('token', DEMO_TOKEN)
    localStorage.setItem('role', 'demo')
    localStorage.setItem('user', JSON.stringify({ id: 'demo', username: '体验管理员' }))
    set({ token: DEMO_TOKEN, role: 'demo', user: { id: 'demo', username: '体验管理员' } })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('role')
    set({ token: null, user: null, role: 'demo' })
  },

  setRole: (role: 'demo' | 'admin') => {
    localStorage.setItem('role', role)
    set({
      role,
      user: { id: role === 'admin' ? 'admin' : 'demo', username: role === 'admin' ? '管理员' : '体验管理员' },
    })
  },
}))
