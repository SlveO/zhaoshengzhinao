const stages = [{ key: 'open', label: '建立信任' }, { key: 'explore', label: '深度探索' }, { key: 'focus', label: '聚焦澄清' }, { key: 'confirm', label: '画像确认' }]
const order = ['open', 'explore', 'focus', 'confirm']

export default function StageIndicator({ current }: { current: string }) {
  const idx = order.indexOf(current)
  return (
    <div className="space-y-1">
      <div className="text-xs uppercase text-muted tracking-wider mb-2">对话阶段</div>
      {stages.map((s, i) => {
        const done = i < idx, active = i === idx
        return (
          <div key={s.key} className={`flex items-center gap-2 px-2 py-1.5 rounded-md ${active ? 'bg-blue-50' : done ? 'opacity-50' : 'opacity-30'}`}>
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white ${active ? 'bg-warning' : done ? 'bg-primary' : 'bg-gray-300'}`}>{done ? '✓' : i + 1}</span>
            <span className={`text-xs font-medium ${active ? 'text-warning' : 'text-text'}`}>{s.label}</span>
          </div>
        )
      })}
    </div>
  )
}
