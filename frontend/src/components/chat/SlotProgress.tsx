import type { ProfileSlot } from '../../types'

export default function SlotProgress({ slots }: { slots: ProfileSlot }) {
  const items = [
    { key: 'score', label: '分数 / 选科', done: !!slots.score },
    { key: 'region_pref', label: '地域偏好', done: (slots.region_pref || []).length > 0 },
    { key: 'riasec', label: '兴趣倾向', done: Object.keys(slots.riasec || {}).length > 0 },
    { key: 'values', label: '价值观排序', done: (slots.values || []).length > 0 },
  ]
  const done = items.filter((i) => i.done).length
  const pct = Math.round((done / items.length) * 100)
  return (
    <div>
      <div className="text-xs uppercase text-muted tracking-wider mb-2">已收集信息</div>
      <div className="space-y-1.5">
        {items.map((i) => (
          <div key={i.key} className={`flex items-center gap-2 text-xs ${i.done ? '' : 'opacity-40'}`}>
            <span className={i.done ? 'text-success' : ''}>{i.done ? '✓' : '○'}</span>
            <span>{i.label}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 bg-border rounded h-1"><div className="bg-primary h-1 rounded transition-all" style={{ width: `${pct}%` }} /></div>
      <div className="text-xs text-muted mt-1 text-right">完成度 {pct}%</div>
    </div>
  )
}
