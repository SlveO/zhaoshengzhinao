import { useEffect, useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useWebSocket } from './useWebSocket'
import api from '../services/api'
import type { ChatMessage } from '../types'

export function useChat() {
  const { sessionId, setSessionId, addMessage, setStage, updateSlots, showSummary } = useChatStore()
  const handleMessage = useCallback((msg: ChatMessage) => {
    if (msg.type === 'thinking') { addMessage(msg); return }
    if (msg.type === 'message' && msg.role === 'assistant') { addMessage(msg) }
    if (msg.type === 'stage_change') { setStage(msg.content || '') }
    if (msg.type === 'profile_update') { updateSlots(msg.value || {}) }
    if (msg.type === 'summary') { showSummary({ stage: msg.stage || '', content: msg.content || '', profile: msg.profile_snapshot || {} }) }
  }, [addMessage, setStage, updateSlots, showSummary])

  const { send } = useWebSocket(sessionId, handleMessage)

  useEffect(() => {
    if (!sessionId) {
      api.post('/chat/session').then((r) => setSessionId(r.data.session_id)).catch(() => setSessionId('mock'))
    }
  }, [sessionId, setSessionId])

  return { send, sessionId }
}
