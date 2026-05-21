import { useState, useMemo } from 'react'

type Priority = 'P0' | 'P1' | 'P2' | 'P3'

const PRIORITY_ORDER: Record<Priority, number> = { P0: 0, P1: 1, P2: 2, P3: 3 }
const PRIORITY_STYLE: Record<Priority, { bg: string; color: string }> = {
  P0: { bg: '#fee2e2', color: '#991b1b' },
  P1: { bg: '#fef3c7', color: '#92400e' },
  P2: { bg: '#dbeafe', color: '#1e40af' },
  P3: { bg: '#f1f5f9', color: '#64748b' },
}

const PROCESS_METHODS = ['已电话联系', '在线对话', '已发材料'] as const
const PROCESS_STYLE: Record<string, { bg: string; color: string }> = {
  '已电话联系': { bg: '#dcfce7', color: '#166534' },
  '在线对话': { bg: '#dbeafe', color: '#1e40af' },
  '已发材料': { bg: '#fef3c7', color: '#92400e' },
  '已忽略': { bg: '#f1f5f9', color: '#64748b' },
}

interface LeadItem {
  id: string; name: string; intentScore: number; province: string; subjectType: string
  score: number; major: string; concerns: string[]; phone: string; priority: Priority
  detail: {
    urgency: string; reason: string; profile: string; coreInterests: string
    suggestedAction: string; materials: string
  }
}

interface ProcessedItem {
  id: string; name: string; intentScore: number; profile: string
  method: string; methodColor: { bg: string; color: string }
  time: string; note: string
}

// TODO: replace with API GET /api/leads?intent=high
const MOCK_LEADS: LeadItem[] = [
  { id: 'A001', name: '学生A', intentScore: 92, priority: 'P0', province: '广东', subjectType: '物理类', score: 585, major: '电子信息方向', concerns: ['就业去向', '转专业', '录取位次'], phone: '138****7241',
    detail: { urgency: '24小时内跟进', reason: '该学生多次追问就业与录取可能性。近期反复提及电子信息类专业的就业去向、转专业条件和近三年录取位次，建议优先引导了解本校电子信息方向的校企合作企业和毕业生就业案例。', profile: '广东 / 物理类 / 585分 / 电子信息方向 · 意向92', coreInterests: '就业去向、转专业政策、近三年录取位次', suggestedAction: '建议招生老师 24 小时内人工跟进。', materials: '电子信息类就业案例、专业培养方案、近三年录取位次说明。' } },
  { id: 'A004', name: '学生D', intentScore: 88, priority: 'P1', province: '江西', subjectType: '物理类', score: 602, major: '计算机科学', concerns: ['就业率', '薪资水平', '校企合作'], phone: '136****4512',
    detail: { urgency: '24小时内电话联系', reason: '高分考生且意向明确，对就业率和薪资高度关注，属于高价值线索。建议由招生组长直接电话联系。', profile: '江西 / 物理类 / 602分 / 计算机科学 · 意向88', coreInterests: '就业率、薪资水平、校企合作', suggestedAction: '招生组长电话联系，发送计算机学院就业报告和合作企业名单。', materials: '计算机学院就业报告、合作企业名单、毕业生薪资分布。' } },
  { id: 'A002', name: '学生B', intentScore: 85, priority: 'P2', province: '湖南', subjectType: '历史类', score: 562, major: '师范方向', concerns: ['保研率', '课程设置'], phone: '139****5823',
    detail: { urgency: '48小时内联系', reason: '该学生对师范类专业表现出明确兴趣，主要关注保研率和课程安排的灵活性。建议在联系时重点介绍本校师范专业的升学数据和个性化培养路径。', profile: '湖南 / 历史类 / 562分 / 师范方向 · 意向85', coreInterests: '保研率、课程设置', suggestedAction: '建议招生老师 48 小时内通过在线对话联系，发送师范专业介绍材料。', materials: '师范专业升学数据、课程设置说明、优秀毕业生案例。' } },
  { id: 'A005', name: '学生E', intentScore: 79, priority: 'P2', province: '福建', subjectType: '历史类', score: 548, major: '法学方向', concerns: ['司法考试通过率'], phone: '135****8763',
    detail: { urgency: '72小时内联系', reason: '学生对法学有明确方向，关注点集中在司法考试通过率，说明已有较强报考意愿。建议发送近三年司法考试数据和优秀校友案例。', profile: '福建 / 历史类 / 548分 / 法学方向 · 意向79', coreInterests: '司法考试通过率', suggestedAction: '在线对话联系，发送法学专业司法考试数据和校友去向。', materials: '近三年司法考试通过率、法学优秀校友案例、专业培养方案。' } },
  { id: 'A003', name: '学生C', intentScore: 71, priority: 'P3', province: '广西', subjectType: '物理类', score: 528, major: '数据科学方向', concerns: ['实验室条件'], phone: '137****3098',
    detail: { urgency: '持续观察', reason: '该学生目前仅在初步了解阶段，咨询频次较低，主要关心实验室硬件条件。可在后续推送相关实验室介绍内容，待意向提升后再主动联系。', profile: '广西 / 物理类 / 528分 / 数据科学方向 · 意向71', coreInterests: '实验室条件', suggestedAction: '暂不主动联系，通过推送实验室介绍内容持续培育意向。', materials: '数据科学实验室介绍、校企合作项目展示。' } },
]

export default function LeadWorkbenchPage() {
  const [leads, setLeads] = useState<LeadItem[]>(MOCK_LEADS)
  const [processed, setProcessed] = useState<ProcessedItem[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [processMethod, setProcessMethod] = useState<string>('已电话联系')
  const [processedExpanded, setProcessedExpanded] = useState(false)

  const selectedLead = leads.find((l) => l.id === selected)
  const displayProcessed = processedExpanded ? processed : processed.slice(0, 3)

  const moveToProcessed = (id: string, method: string) => {
    const lead = leads.find((l) => l.id === id)
    if (!lead) return
    const now = new Date()
    const item: ProcessedItem = {
      id, name: lead.name, intentScore: lead.intentScore,
      profile: `${lead.province} / ${lead.subjectType} / ${lead.score}`,
      method, methodColor: PROCESS_STYLE[method] || PROCESS_STYLE['已电话联系'],
      time: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`,
      note: method === '已忽略' ? '已从待处理中移除' : '',
    }
    setProcessed((prev) => [item, ...prev])
    setLeads((prev) => prev.filter((l) => l.id !== id))
    if (selected === id) setSelected(null)
  }

  const ignoreLead = (id: string) => moveToProcessed(id, '已忽略')

  const updatePriority = (id: string, p: Priority) => {
    setLeads((prev) => {
      const next = prev.map((l) => (l.id === id ? { ...l, priority: p } : l))
      next.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
      return next
    })
  }

  const sortOptions = useMemo(() => ['按优先级降序', '按时间最新', '按分数降序'], [])
  const [sortBy, setSortBy] = useState('按优先级降序')

  const sortedLeads = useMemo(() => {
    const arr = [...leads]
    if (sortBy === '按优先级降序') {
      arr.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
    } else if (sortBy === '按分数降序') {
      arr.sort((a, b) => b.score - a.score)
    }
    // 按时间最新 keeps original order for now (mock data has no timestamp)
    return arr
  }, [leads, sortBy])

  return (
    <div>
      {/* Main Card */}
      <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 14 }}>
        <div style={{
          padding: '14px 18px', borderBottom: '1px solid var(--color-border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 2px', letterSpacing: '-0.02em' }}>
              高意向生源工作台
            </h2>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              今日新增 <b style={{ color: 'var(--color-brand-800)' }}>18</b> 条高意向线索
            </div>
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            style={{
              padding: '5px 10px', border: '1px solid var(--color-border)',
              borderRadius: 6, fontSize: 12, fontFamily: 'inherit', background: '#f8fafc',
            }}
          >
            {sortOptions.map((o) => <option key={o}>{o}</option>)}
          </select>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th style={{ width: '8%', textAlign: 'center' }}>优先级</th>
                <th style={{ width: '18%' }}>学生</th>
                <th>画像与关注点</th>
                <th style={{ width: '22%', textAlign: 'center' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {sortedLeads.map((lead) => (
                <tr
                  key={lead.id}
                  className={selected === lead.id ? 'selected' : ''}
                  style={{
                    cursor: 'pointer',
                    borderLeft: selected === lead.id ? '3px solid var(--color-brand-800)' : '3px solid transparent',
                  }}
                  onClick={() => setSelected(selected === lead.id ? null : lead.id)}
                >
                  <td style={{ padding: '8px 0', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                    <select
                      value={lead.priority}
                      onChange={(e) => updatePriority(lead.id, e.target.value as Priority)}
                      style={{
                        fontSize: 10, fontWeight: 600, padding: '2px 6px', borderRadius: 8,
                        border: '1px solid #e5e9f2', cursor: 'pointer', fontFamily: 'inherit',
                        background: PRIORITY_STYLE[lead.priority].bg,
                        color: PRIORITY_STYLE[lead.priority].color,
                      }}
                    >
                      <option>P0</option><option>P1</option><option>P2</option><option>P3</option>
                    </select>
                  </td>
                  <td style={{ padding: '10px 0' }}>
                    <span style={{ fontWeight: 600 }}>{lead.name}</span>
                    <span className="pill pill-blue" style={{ marginLeft: 8 }}>
                      意向 {lead.intentScore}
                    </span>
                  </td>
                  <td style={{ padding: '10px 0' }}>
                    <div style={{ fontWeight: 500 }}>
                      {lead.province} / {lead.subjectType} / {lead.score}分
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '2px 0' }}>
                      {lead.major}
                    </div>
                    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                      {lead.concerns.map((c) => (
                        <span key={c} style={{
                          fontSize: 10, background: '#f1f5f9', padding: '1px 6px',
                          borderRadius: 3, color: 'var(--color-text-secondary)',
                        }}>
                          {c}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td style={{ padding: '10px 0', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                    <div style={{ display: 'flex', gap: 4, justifyContent: 'center' }}>
                      <button
                        onClick={() => moveToProcessed(lead.id, '已电话联系')}
                        style={{
                          padding: '4px 10px', border: '1px solid #bfdbfe', background: '#fff',
                          borderRadius: 5, cursor: 'pointer', fontSize: 10, fontFamily: 'inherit',
                          color: 'var(--color-brand-800)', display: 'flex', alignItems: 'center', gap: 3,
                        }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                        电话
                      </button>
                      <button
                        onClick={() => moveToProcessed(lead.id, '在线对话')}
                        style={{
                          padding: '4px 10px', border: '1px solid #bfdbfe', background: '#fff',
                          borderRadius: 5, cursor: 'pointer', fontSize: 10, fontFamily: 'inherit',
                          color: 'var(--color-brand-800)', display: 'flex', alignItems: 'center', gap: 3,
                        }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        在线
                      </button>
                      <button
                        onClick={() => ignoreLead(lead.id)}
                        style={{
                          padding: '4px 10px', border: '1px solid #fee2e2', background: '#fff',
                          borderRadius: 5, cursor: 'pointer', fontSize: 10, fontFamily: 'inherit',
                          color: '#f5222d', display: 'flex', alignItems: 'center', gap: 3,
                        }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                        忽略
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {sortedLeads.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 40 }}>
                    暂无待处理线索
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Panel */}
      {selectedLead && (
        <div className="card" style={{
          marginBottom: 14, borderLeft: '3px solid var(--color-brand-800)',
          animation: 'page-enter 0.2s ease',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <b style={{ fontSize: 14 }}>{selectedLead.name} · 线索建议</b>
              <span style={{
                background: selectedLead.priority === 'P0' ? '#fee2e2' : '#fef3c7',
                color: selectedLead.priority === 'P0' ? '#991b1b' : '#92400e',
                padding: '2px 8px', borderRadius: 10, fontSize: 9, fontWeight: 600,
              }}>
                {selectedLead.detail.urgency}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <select
                  value={processMethod}
                  onChange={(e) => setProcessMethod(e.target.value)}
                  style={{
                    padding: '4px 8px', border: '1px solid #22c55e', background: '#fff',
                    borderRadius: '5px 0 0 5px', fontSize: 10, fontFamily: 'inherit',
                    cursor: 'pointer', color: '#166534', borderRight: 0,
                  }}
                >
                  {PROCESS_METHODS.map((m) => <option key={m}>{m}</option>)}
                </select>
                <button
                  onClick={() => moveToProcessed(selectedLead.id, processMethod)}
                  style={{
                    padding: '4px 10px', background: '#22c55e', color: '#fff', border: 'none',
                    borderRadius: '0 5px 5px 0', fontSize: 10, fontFamily: 'inherit',
                    cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 3,
                    whiteSpace: 'nowrap',
                  }}
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                  标记已处理
                </button>
              </div>
              <button
                onClick={() => ignoreLead(selectedLead.id)}
                className="btn btn-sm"
                style={{
                  display: 'flex', alignItems: 'center', gap: 3, fontSize: 11,
                  border: '1px solid #fee2e2', color: '#f5222d', background: '#fff',
                }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                忽略
              </button>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 18 }}>
            <div style={{ flex: 1.2 }}>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>
                {selectedLead.detail.reason}
              </div>
            </div>
            <div style={{ flex: 0.8, borderLeft: '1px solid var(--color-border)', paddingLeft: 16 }}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 2 }}>学生画像</div>
              <div style={{ fontSize: 12, fontWeight: 500 }}>{selectedLead.detail.profile}</div>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 10, marginBottom: 2 }}>核心关注</div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{selectedLead.detail.coreInterests}</div>
            </div>
            <div style={{ flex: 0.8, borderLeft: '1px solid var(--color-border)', paddingLeft: 16 }}>
              <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 2 }}>推荐材料</div>
              <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>{selectedLead.detail.materials}</div>
            </div>
          </div>
        </div>
      )}

      {/* Processed Section */}
      {processed.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{
            padding: '12px 16px', borderBottom: processedExpanded || processed.length <= 3 ? '1px solid var(--color-border)' : 'none',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            background: '#f8fafc',
          }}>
            <div>
              <b style={{ fontSize: 13 }}>已处理线索</b>
              <span style={{ fontSize: 10, color: 'var(--color-text-muted)', marginLeft: 8 }}>
                已处理 {processed.length} 条
              </span>
            </div>
            {processed.length > 3 && (
              <button
                onClick={() => setProcessedExpanded((v) => !v)}
                className="btn btn-sm btn-secondary"
                style={{ fontSize: 10 }}
              >
                {processedExpanded ? '收起' : '展开全部'}
              </button>
            )}
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>学生</th><th>画像</th><th>处理方式</th><th>处理时间</th><th>备注</th>
                </tr>
              </thead>
              <tbody>
                {displayProcessed.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <span style={{ fontWeight: 500 }}>{p.name}</span>
                      <span style={{ color: 'var(--color-text-muted)', fontSize: 11, marginLeft: 6 }}>
                        意向 {p.intentScore}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{p.profile}</td>
                    <td>
                      <span style={{
                        background: p.methodColor.bg, color: p.methodColor.color,
                        padding: '2px 8px', borderRadius: 8, fontSize: 10,
                      }}>
                        {p.method}
                      </span>
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{p.time}</td>
                    <td style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{p.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
