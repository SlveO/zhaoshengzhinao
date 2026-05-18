import { create } from 'zustand'
import api from '../api/client'
import type { LoginResponse } from '../types'

interface AuthState {
  token: string | null
  user: { id: string; username: string } | null
  login: (username: string, password: string, tenantSlug: string) => Promise<void>
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

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ token: null, user: null })
  },
}))
