import { useEffect, useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useWebSocket } from './useWebSocket'
import api from '../services/api'
import type { ChatMessage } from '../types'

export function useChat() {
  const { sessionId, setSessionId, addMessage, setStage, updateSlots, showSummary } = useChatStore()

  const handleMessage = useCallback((msg: ChatMessage) => {
    if (msg.type === 'thinking') { addMessage(msg); return }
    if (msg.type === 'message' && msg.role === 'assistant') {
      addMessage(msg)
      if (msg.stage) setStage(msg.stage)
      return
    }
    if (msg.type === 'stage_change') {
      if (msg.to) setStage(msg.to)
      return
    }
    if (msg.type === 'profile_update') { updateSlots(msg.value || {}); return }
    if (msg.type === 'summary') { showSummary({ stage: msg.stage || '', content: msg.content || '', profile: msg.profile_snapshot || {} }); return }
  }, [addMessage, setStage, updateSlots, showSummary])

  const { send: wsSend } = useWebSocket(sessionId, handleMessage)

  const send = useCallback((content: string) => {
    addMessage({ type: 'message', role: 'user', content })
    wsSend(content)
  }, [wsSend, addMessage])

  const createSession = useCallback(async () => {
    try {
      const r = await api.post('/chat/session')
      setSessionId(r.data.session_id)
      return r.data.session_id
    } catch {
      setSessionId('mock')
      return null
    }
  }, [setSessionId])

  return { send, sessionId, createSession }
}
