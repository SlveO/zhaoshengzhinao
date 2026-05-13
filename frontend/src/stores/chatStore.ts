import { create } from 'zustand'
import type { ChatMessage, ProfileSlot } from '../types'

interface ChatState {
  sessionId: string | null
  stage: string
  messages: ChatMessage[]
  slots: ProfileSlot
  summaryPending: boolean
  summaryData: { stage: string; content: string; profile: any } | null
  setSessionId: (id: string) => void
  addMessage: (msg: ChatMessage) => void
  setStage: (stage: string) => void
  updateSlots: (slots: ProfileSlot) => void
  showSummary: (data: any) => void
  dismissSummary: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  sessionId: null, stage: 'open', messages: [], slots: {}, summaryPending: false, summaryData: null,
  setSessionId: (id) => set({ sessionId: id }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setStage: (stage) => set({ stage }),
  updateSlots: (slots) => set({ slots }),
  showSummary: (data) => set({ summaryPending: true, summaryData: data }),
  dismissSummary: () => set({ summaryPending: false, summaryData: null }),
}))
