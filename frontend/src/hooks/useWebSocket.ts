import { useEffect, useRef, useCallback } from 'react'

export function useWebSocket(sessionId: string | null, onMessage: (msg: any) => void) {
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/chat/session/${sessionId}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onmessage = (event) => { onMessage(JSON.parse(event.data)) }
    ws.onerror = () => console.error('WebSocket error')
    return () => { ws.close() }
  }, [sessionId])

  const send = useCallback((content: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'message', content, session_id: sessionId }))
    }
  }, [sessionId])

  return { send }
}
