import type { ChatMessage } from '../../types'

export default function ChatBubble({ msg }: { msg: ChatMessage }) {
  if (msg.type === 'thinking') {
    return (
      <div className="flex gap-3 max-w-[80%]">
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs flex-shrink-0">AI</div>
        <div className="bg-card rounded-xl px-4 py-3 flex gap-1.5 items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '0.15s' }} />
          <span className="w-1.5 h-1.5 rounded-full bg-gray-300 animate-bounce" style={{ animationDelay: '0.3s' }} />
          <span className="text-muted ml-1 text-sm">{msg.message || '正在分析...'}</span>
        </div>
      </div>
    )
  }
  const isAI = msg.role === 'assistant'
  return (
    <div className={`flex gap-3 max-w-[80%] ${isAI ? '' : 'self-end flex-row-reverse'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-xs flex-shrink-0 ${isAI ? 'bg-primary' : 'bg-warm'}`}>{isAI ? 'AI' : '我'}</div>
      <div>
        <div className={`rounded-xl px-4 py-3 leading-relaxed text-sm ${isAI ? 'bg-card text-text' : 'bg-primary text-white'}`}>{msg.content}</div>
        {msg.stage && <div className="text-xs text-muted mt-1 px-1">{msg.stage === 'open' ? '建立信任' : msg.stage === 'explore' ? '深度探索' : msg.stage === 'focus' ? '聚焦澄清' : msg.stage === 'confirm' ? '画像确认' : msg.stage}</div>}
      </div>
    </div>
  )
}
