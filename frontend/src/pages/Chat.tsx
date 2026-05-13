import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useChatStore } from '../stores/chatStore'
import { useChat } from '../hooks/useChat'
import StageIndicator from '../components/chat/StageIndicator'
import SlotProgress from '../components/chat/SlotProgress'
import ChatBubble from '../components/chat/ChatBubble'
import ChatInput from '../components/chat/ChatInput'
import SummaryModal from '../components/chat/SummaryModal'

export default function Chat() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { send } = useChat()
  const { stage, messages, slots, summaryPending, summaryData, dismissSummary, updateSlots } = useChatStore()
  const nav = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll: always scroll to bottom when new messages arrive
  // Uses scrollTop direct assignment (instant) to avoid smooth-scroll
  // animation conflicts with rapid-fire messages (thinking -> reply)
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150
    if (isNearBottom) {
      container.scrollTop = container.scrollHeight
    }
  }, [messages])

  const handleSend = (text: string) => { send(text) }

  const handleConfirm = () => {
    dismissSummary()
    if (stage === 'confirm' || stage === 'done') nav('/recommendations')
  }

  const handleModify = (field: string, _value: any) => {
    dismissSummary()
  }

  return (
    <div className="flex h-[calc(100vh-53px)]">
      {/* Sidebar toggle button - always visible in one place */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-6 h-12 bg-white border border-border border-l-0 rounded-r-lg flex items-center justify-center hover:bg-gray-50 transition shadow-sm"
        style={{ marginLeft: sidebarOpen ? '260px' : '0' }}
        title={sidebarOpen ? '收起侧栏' : '展开侧栏'}
      >
        <span className="text-muted text-sm">{sidebarOpen ? '◀' : '▶'}</span>
      </button>

      {/* Sidebar */}
      {sidebarOpen && (
        <div className="w-[260px] bg-gray-50/80 border-r border-border p-4 flex flex-col gap-6 flex-shrink-0">
          <StageIndicator current={stage} />
          <SlotProgress slots={slots} />
          <Link to="/recommendations" className="text-xs text-primary hover:underline mt-auto">
            跳过对话，直接查看推荐 →
          </Link>
        </div>
      )}

      {/* Main chat */}
      <div className="flex-1 flex flex-col bg-white">
        <div className="px-4 py-2 border-b border-gray-100">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted">
              第 <span className="text-warning font-semibold">{stage === 'open' ? '1' : stage === 'explore' ? '2' : stage === 'focus' ? '3' : stage === 'confirm' ? '4' : stage === 'done' ? '✓' : '?'}</span> / 4 阶段：
              <span className="font-semibold ml-1">{stage === 'open' ? '建立信任' : stage === 'explore' ? '深度探索' : stage === 'focus' ? '聚焦澄清' : stage === 'confirm' ? '画像确认' : stage === 'done' ? '已完成' : stage}</span>
            </span>
            <span className="text-xs text-muted">{stage === 'done' ? '可查看推荐' : '继续对话完善画像'}</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div className="bg-primary h-1.5 rounded-full transition-all duration-500" style={{
              width: stage === 'open' ? '25%' : stage === 'explore' ? '50%' : stage === 'focus' ? '75%' : stage === 'confirm' ? '90%' : stage === 'done' ? '100%' : '10%'
            }} />
          </div>
        </div>

        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto px-4 py-5 space-y-4" style={{ minHeight: 0 }}>
          {messages.length === 0 && (
            <div className="flex gap-3 max-w-[80%]">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs flex-shrink-0">AI</div>
              <div>
                <div className="bg-card rounded-xl px-4 py-3 leading-relaxed text-text">
                  同学你好！我是你的高考志愿填报助手。<br />
                  不管这次考试结果怎么样，我们先聊聊你对未来的想法吧——你平时学习或者生活中，做什么事情会让你觉得特别投入、时间过得很快？
                </div>
                <div className="text-xs text-muted mt-1 px-1">建立信任</div>
              </div>
            </div>
          )}
          {messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-4 border-t border-gray-100"><ChatInput onSend={handleSend} /></div>
      </div>

      {summaryPending && summaryData && (
        <SummaryModal
          stage={summaryData.stage}
          profile={summaryData.profile}
          onConfirm={handleConfirm}
          onModify={handleModify}
          onDismiss={dismissSummary}
        />
      )}
    </div>
  )
}
