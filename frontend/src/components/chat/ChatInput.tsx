import { useState } from 'react'

export default function ChatInput({ onSend, disabled }: { onSend: (text: string) => void; disabled?: boolean }) {
  const [text, setText] = useState('')
  const handle = () => { if (text.trim()) { onSend(text.trim()); setText('') } }
  return (
    <div className="flex gap-3">
      <input className="flex-1 px-5 py-3 border border-border rounded-full text-sm focus:outline-none focus:ring-2 focus:ring-primary" placeholder="输入你的想法..." value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handle()} disabled={disabled} />
      <button onClick={handle} disabled={disabled} className="w-11 h-11 rounded-full bg-primary text-white flex items-center justify-center hover:bg-primaryDark transition disabled:opacity-50 text-lg">{'➤'}</button>
    </div>
  )
}
