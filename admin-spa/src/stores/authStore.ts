import { create } from 'zustand'
import api from '../api/client'
import type { LoginResponse } from '../types'

interface AuthState {
  token: string | null
  user: { id: string; username: string } | null
  login: (username: string, password: string, tenantSlug: string) => Promise<void>
  loginDemo: (tenantSlug: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),

  login: async (username: string, password: string, tenantSlug: string) => {
    localStorage.setItem('tenantSlug', tenantSlug)
    const res = await api.post<LoginResponse>('/auth/login', { username, password })
    const { access_token, user_id, username: uname } = res.data
    localStorage.setItem('token', access_token)
    localStorage.setItem('user', JSON.stringify({ id: user_id, username: uname }))
    set({ token: access_token, user: { id: user_id, username: uname } })
  },

  loginDemo: async (tenantSlug: string) => {
    // 体验模式：用真实 demo 账号登录，token 走正常流程
    localStorage.setItem('tenantSlug', tenantSlug)
    try {
      const res = await api.post<LoginResponse>('/auth/login', { username: 'admin', password: 'admin123' })
      const { access_token, user_id, username: uname } = res.data
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify({ id: user_id, username: uname }))
      set({ token: access_token, user: { id: user_id, username: uname } })
    } catch {
      // 如果登录失败，至少设置 tenant，让用户手动登录
      set({ token: null, user: null })
    }
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null })
  },
}))
