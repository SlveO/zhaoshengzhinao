import { create } from 'zustand'
import { authApi } from '../services/auth'

interface AuthState {
  user: { user_id: string; username: string } | null
  accessToken: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string, region: string, score: number, subjects: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  login: async (username, password) => {
    const { data } = await authApi.login(username, password)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    set({ user: { user_id: data.user_id, username: data.username }, accessToken: data.access_token, isAuthenticated: true })
  },
  register: async (username, password, region, score, subjects) => {
    const { data } = await authApi.register(username, password, region, score, subjects)
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    set({ user: { user_id: data.user_id, username: data.username }, accessToken: data.access_token, isAuthenticated: true })
  },
  logout: () => {
    localStorage.clear()
    set({ user: null, accessToken: null, isAuthenticated: false })
  },
}))
