import type { ProfileSlot } from '../../types'

const RIASEC_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  R: { label: '动手操作', color: '#1E40AF', bg: '#DBEAFE' },
  I: { label: '研究思考', color: '#065F46', bg: '#D1FAE5' },
  A: { label: '艺术创造', color: '#6D28D9', bg: '#EDE9FE' },
  S: { label: '帮助他人', color: '#92400E', bg: '#FEF3C7' },
  E: { label: '领导说服', color: '#BE185D', bg: '#FCE7F3' },
  C: { label: '规范有序', color: '#0369A1', bg: '#E0F2FE' },
}

function getCompletenessLabel(level?: string) {
  switch (level) {
    case 'L4': return { text: '已确认', color: '#065F46', bg: '#D1FAE5' }
    case 'L3': return { text: '深度画像', color: '#6D28D9', bg: '#EDE9FE' }
    case 'L2': return { text: '较完整', color: '#92400E', bg: '#FEF3C7' }
    default: return { text: '基础画像', color: '#64748B', bg: '#F1F5F9' }
  }
}

export default function EvidenceProgress({ slots }: { slots: ProfileSlot }) {
  const riasec = slots.riasec || {}
  const dims = ['R', 'I', 'A', 'S', 'E', 'C']
  const covered = dims.filter(d => riasec[d] !== undefined).length
  const pct = Math.round((covered / 6) * 100)
  const cLevel = getCompletenessLabel(slots.completeness)

  return (
    <div>
      <div className="text-xs uppercase text-muted tracking-wider mb-2">已收集信息</div>

      {/* Basics */}
      <div className="space-y-1 mb-3">
        <div className={`flex items-center gap-2 text-xs ${slots.score ? '' : 'opacity-40'}`}>
          <span className={slots.score ? 'text-success' : ''}>{slots.score ? '✓' : '○'}</span>
          <span>分数 / 选科</span>
        </div>
        <div className={`flex items-center gap-2 text-xs ${(slots.region_pref || []).length > 0 ? '' : 'opacity-40'}`}>
          <span className={(slots.region_pref || []).length > 0 ? 'text-success' : ''}>{(slots.region_pref || []).length > 0 ? '✓' : '○'}</span>
          <span>地域偏好</span>
        </div>
      </div>

      {/* RIASEC hex grid */}
      <div className="text-xs text-muted mb-1.5">RIASEC 兴趣倾向</div>
      <div className="grid grid-cols-3 gap-1 mb-3">
        {dims.map(d => {
          const info = RIASEC_LABELS[d]
          const score = riasec[d]
          const done = score !== undefined
          return (
            <div key={d} className={`rounded-lg p-1.5 text-center border transition-all ${done ? 'border-current' : 'border-border opacity-40'}`} style={done ? { borderColor: info.color, background: info.bg } : {}}>
              <div className="text-xs font-bold" style={done ? { color: info.color } : {}}>{d}</div>
              <div className="text-[9px] text-muted leading-tight">{info.label}</div>
              {done && <div className="text-[10px] font-bold mt-0.5" style={{ color: info.color }}>{score}</div>}
            </div>
          )
        })}
      </div>

      {/* Values */}
      <div className={`flex items-center gap-2 text-xs mb-3 ${(slots.values || []).length > 0 ? '' : 'opacity-40'}`}>
        <span className={(slots.values || []).length > 0 ? 'text-success' : ''}>{(slots.values || []).length > 0 ? '✓' : '○'}</span>
        <span>价值观排序 ({slots.values?.length || 0}/2)</span>
      </div>

      {/* Completeness badge */}
      <div className="flex items-center justify-between">
        <span className="text-xs px-2 py-0.5 rounded-full font-semibold" style={{ color: cLevel.color, background: cLevel.bg }}>{cLevel.text}</span>
        <span className="text-xs text-muted">{covered}/6 维度</span>
      </div>

      {/* Progress bar */}
      <div className="mt-2 bg-border rounded h-1">
        <div className="bg-primary h-1 rounded transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-muted mt-1 text-right">完成度 {pct}%</div>
    </div>
  )
}
