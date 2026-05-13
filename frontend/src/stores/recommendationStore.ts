import { create } from 'zustand'
import type { Recommendation } from '../types'
import { recApi } from '../services/recommendation'

interface RecState {
  recommendations: Recommendation[]
  profileSnapshot: any
  filters: { level: string; city: string; category: string }
  loading: boolean
  load: () => Promise<void>
  setFilter: (key: string, value: string) => void
}

export const useRecStore = create<RecState>((set, get) => ({
  recommendations: [],
  profileSnapshot: null,
  filters: { level: '', city: '', category: '' },
  loading: false,
  load: async () => {
    set({ loading: true })
    try {
      const { data } = await recApi.getRecommendations()
      set({
        recommendations: data.recommendations || [],
        profileSnapshot: data.profile_snapshot,
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },
  setFilter: (key, value) =>
    set({ filters: { ...get().filters, [key]: value } }),
}))
