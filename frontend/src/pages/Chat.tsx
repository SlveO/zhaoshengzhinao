import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
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

  const handleSend = (text: string) => { send(text) }

  const handleConfirm = () => {
    dismissSummary()
    if (stage === 'confirm' || stage === 'done') nav('/recommendations')
  }

  const handleModify = (field: string, _value: any) => {
    dismissSummary()
    if (field === 'region_pref' || field === 'values') {
      // Let AI re-ask about this field
    }
  }

  return (
    <div className="flex h-[calc(100vh-53px)]">
      {sidebarOpen && (
        <div className="w-[260px] bg-gray-50/80 border-r border-border p-4 flex flex-col gap-6 flex-shrink-0">
          <StageIndicator current={stage} />
          <SlotProgress slots={slots} />
          <button onClick={() => setSidebarOpen(false)} className="text-xs text-muted hover:text-text mt-auto">{'»'} 收起侧栏</button>
        </div>
      )}

      <div className="flex-1 flex flex-col bg-white">
        {!sidebarOpen && <button onClick={() => setSidebarOpen(true)} className="text-xs text-muted p-2 hover:text-text">{'«'} 展开侧栏</button>}
        <div className="px-4 py-2 border-b border-gray-100 text-xs text-muted">
          正在进行：<span className="text-warning font-semibold ml-1">{stage === 'open' ? '建立信任' : stage === 'explore' ? '深度探索' : stage === 'focus' ? '聚焦澄清' : stage === 'confirm' ? '画像确认' : stage}</span>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-muted py-20">开始对话，让 AI 了解你的兴趣和价值观</div>
          )}
          {messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
        </div>
        <div className="p-4 border-t border-gray-100"><ChatInput onSend={handleSend} /></div>
      </div>

      {summaryPending && summaryData && (
        <SummaryModal stage={summaryData.stage} profile={summaryData.profile} onConfirm={handleConfirm} onModify={handleModify} onDismiss={dismissSummary} />
      )}
    </div>
  )
}
