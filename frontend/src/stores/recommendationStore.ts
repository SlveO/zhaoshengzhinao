import { create } from 'zustand'
import type { Recommendation } from '../types'
import { recApi } from '../services/recommendation'

interface RecState {
  recommendations: Recommendation[]
  profileSnapshot: any
  filters: { level: string; city: string; category: string }
  loading: boolean
  error: string | null
  load: () => Promise<void>
  setFilter: (key: string, value: string) => void
}

export const useRecStore = create<RecState>((set, get) => ({
  recommendations: [],
  profileSnapshot: null,
  filters: { level: '', city: '', category: '' },
  loading: false,
  error: null,
  load: async () => {
    set({ loading: true, error: null })
    try {
      const { data } = await recApi.getRecommendations()
      const recs = data.recommendations || []
      if (recs.length === 0) {
        set({ error: '服务器返回空结果，请先完成对话获得画像再查看推荐', loading: false })
      } else {
        set({
          recommendations: recs,
          profileSnapshot: data.profile_snapshot,
          loading: false,
          error: null,
        })
      }
    } catch {
      set({
        loading: false,
        error: '加载超时，请重试。推荐生成需要调用 AI 分析，约需 15-30 秒',
      })
    }
  },
  setFilter: (key, value) =>
    set({ filters: { ...get().filters, [key]: value } }),
}))
