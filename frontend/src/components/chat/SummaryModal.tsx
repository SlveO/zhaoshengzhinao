interface Props { stage: string; profile: any; onConfirm: () => void; onModify: (field: string, value: any) => void; onDismiss: () => void }

function slotToRows(profile: any): { key: string; icon: string; label: string; value: string; complex: boolean }[] {
  const rows: any[] = []
  if (profile.score) rows.push({ key: 'score', icon: '📊', label: '分数', value: String(profile.score), complex: false })
  if (profile.riasec && Object.keys(profile.riasec).length > 0) {
    const n: Record<string, string> = { R: '动手', I: '研究', A: '创造', S: '助人', E: '领导', C: '规范' }
    const top = Object.entries(profile.riasec as Record<string, number>).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([k]) => n[k] || k).join(' + ')
    rows.push({ key: 'riasec', icon: '🔬', label: '兴趣类型', value: top, complex: true })
  }
  if (profile.values?.length) rows.push({ key: 'values', icon: '🎯', label: '价值观', value: profile.values.join(' > '), complex: false })
  if (profile.region_pref?.length) rows.push({ key: 'region_pref', icon: '🌍', label: '地域偏好', value: profile.region_pref.join(', '), complex: false })
  return rows
}

const stageNames: Record<string, string> = { open: '建立信任', explore: '深度探索', focus: '聚焦澄清', confirm: '画像确认' }

export default function SummaryModal({ stage, profile, onConfirm, onModify, onDismiss }: Props) {
  const rows = slotToRows(profile)
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onDismiss} />
      <div className="relative bg-white rounded-2xl p-6 w-[440px] max-w-[90vw] shadow-xl">
        <div className="flex items-center gap-3 mb-5">
          <span className="text-2xl">{'📋'}</span>
          <div><div className="font-bold text-lg text-text">阶段小结：{stageNames[stage] || stage}完成</div><div className="text-sm text-muted">请确认或修改以下信息</div></div>
        </div>
        <div className="space-y-2 mb-5">
          {rows.map((r) => (
            <div key={r.key} className="bg-blue-50/50 rounded-xl p-3 flex gap-3 items-center">
              <span className="text-xl">{r.icon}</span>
              <div className="flex-1"><div className="text-xs text-muted">{r.label}</div><div className="font-semibold text-text text-sm">{r.value}</div></div>
              <button onClick={() => onModify(r.key, profile[r.key])} className="text-primary text-xs hover:underline">修改</button>
            </div>
          ))}
        </div>
        <div className="flex gap-3">
          <button onClick={onDismiss} className="flex-1 py-2.5 border border-border rounded-lg text-text hover:bg-gray-50 transition text-sm">我再看一下对话</button>
          <button onClick={onConfirm} className="flex-[2] py-2.5 bg-primary text-white rounded-lg font-semibold hover:bg-primaryDark transition text-sm">确认，进入下一阶段</button>
        </div>
      </div>
    </div>
  )
}
