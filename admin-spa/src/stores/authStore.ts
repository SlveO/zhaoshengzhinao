import { create } from 'zustand'
import api from '../api/client'
import type { LoginResponse } from '../types'

interface AuthState {
  token: string | null
  user: { id: string; username: string; is_developer?: boolean; role?: string | null } | null
  role: 'admin' | 'developer'
  login: (username: string, password: string, tenantSlug: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  role: (localStorage.getItem('role') as 'admin' | 'developer') || 'admin',

  login: async (username: string, password: string, tenantSlug: string) => {
    localStorage.setItem('tenantSlug', tenantSlug)
    const res = await api.post<LoginResponse>('/auth/login', { username, password })
    const { access_token, user_id, username: uname, is_developer, role } = res.data
    const userRole = role === 'developer' ? 'developer' : 'admin'
    const userObj = {
      id: user_id,
      username: uname,
      is_developer: is_developer ?? false,
      role: role ?? null,
    }
    localStorage.setItem('token', access_token)
    localStorage.setItem('role', userRole)
    localStorage.setItem('user', JSON.stringify(userObj))
    set({ token: access_token, role: userRole, user: userObj })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('role')
    set({ token: null, user: null, role: 'admin' })
  },
}))
