import { useState, useMemo } from 'react'
import { useMobileStore } from '../stores/mobileStore'
import { Phone, MessageCircle, FileText, ArrowUpDown, Flame, BarChart3, Clock } from 'lucide-react'
import BottomSheet from '../components/BottomSheet'

type Priority = 'P0' | 'P1' | 'P2' | 'P3'
type PageTab = 'pending' | 'processed'

const PRIORITY_ORDER: Record<Priority, number> = { P0: 0, P1: 1, P2: 2, P3: 3 }
const PRIORITY_STYLE: Record<Priority, { bg: string; color: string }> = {
  P0: { bg: '#fee2e2', color: '#991b1b' },
  P1: { bg: '#fef3c7', color: '#92400e' },
  P2: { bg: '#dbeafe', color: '#1e40af' },
  P3: { bg: '#f1f5f9', color: '#64748b' },
}


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

// TODO: replace with API
const MOCK_LEADS: LeadItem[] = [
  { id: 'A001', name: '学生A', intentScore: 92, priority: 'P0', province: '广东', subjectType: '物理类', score: 585, major: '电子信息方向', concerns: ['就业去向', '转专业', '录取位次'], phone: '13872415203',
    detail: { urgency: '24小时内跟进', reason: '该学生多次追问就业与录取可能性。近期反复提及电子信息类专业的就业去向、转专业条件和近三年录取位次，建议优先引导了解本校电子信息方向的校企合作企业和毕业生就业案例。', profile: '广东 / 物理类 / 585分 / 电子信息方向', coreInterests: '就业去向、转专业政策、近三年录取位次', suggestedAction: '建议招生老师 24 小时内人工跟进。', materials: '电子信息类就业案例、专业培养方案、近三年录取位次说明。' } },
  { id: 'A004', name: '学生D', intentScore: 88, priority: 'P1', province: '江西', subjectType: '物理类', score: 602, major: '计算机科学', concerns: ['就业率', '薪资水平', '校企合作'], phone: '13645127890',
    detail: { urgency: '24小时内电话联系', reason: '高分考生且意向明确，对就业率和薪资高度关注，属于高价值线索。', profile: '江西 / 物理类 / 602分 / 计算机科学', coreInterests: '就业率、薪资水平、校企合作', suggestedAction: '招生组长电话联系。', materials: '计算机学院就业报告、合作企业名单。' } },
  { id: 'A002', name: '学生B', intentScore: 85, priority: 'P2', province: '湖南', subjectType: '历史类', score: 562, major: '师范方向', concerns: ['保研率', '课程设置'], phone: '13958237654',
    detail: { urgency: '48小时内联系', reason: '该学生对师范类专业表现出明确兴趣，主要关注保研率和课程安排。', profile: '湖南 / 历史类 / 562分 / 师范方向', coreInterests: '保研率、课程设置', suggestedAction: '在线对话联系。', materials: '师范专业升学数据、课程设置说明。' } },
  { id: 'A005', name: '学生E', intentScore: 79, priority: 'P2', province: '福建', subjectType: '历史类', score: 548, major: '法学方向', concerns: ['司法考试通过率'], phone: '13587634521',
    detail: { urgency: '72小时内联系', reason: '学生对法学有明确方向，关注司法考试通过率。', profile: '福建 / 历史类 / 548分 / 法学方向', coreInterests: '司法考试通过率', suggestedAction: '在线对话联系。', materials: '近三年司法考试通过率、法学优秀校友案例。' } },
  { id: 'A003', name: '学生C', intentScore: 71, priority: 'P3', province: '广西', subjectType: '物理类', score: 528, major: '数据科学方向', concerns: ['实验室条件'], phone: '13730985678',
    detail: { urgency: '持续观察', reason: '该学生目前仅在初步了解阶段，咨询频次较低。', profile: '广西 / 物理类 / 528分 / 数据科学方向', coreInterests: '实验室条件', suggestedAction: '暂不主动联系，推送实验室介绍内容。', materials: '数据科学实验室介绍。' } },
]

const PAGE_SIZE = 10

export default function LeadWorkbenchPage() {
  const isMobile = useMobileStore((s) => s.isMobile)
  const [tab, setTab] = useState<PageTab>('pending')
  const [leads, setLeads] = useState<LeadItem[]>(MOCK_LEADS)
  const [processed, setProcessed] = useState<ProcessedItem[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [showPhone, setShowPhone] = useState<string | null>(null)
  const [processMenu, setProcessMenu] = useState<string | null>(null)
  const processMethod = '已电话联系'
  const [processedPage, setProcessedPage] = useState(0)
  const [sortBy, setSortBy] = useState('按优先级降序')
  const [sortSheetOpen, setSortSheetOpen] = useState(false)
  const [priorityTarget, setPriorityTarget] = useState<string | null>(null)

  const selectedLead = leads.find((l) => l.id === selected)

  const sortedLeads = useMemo(() => {
    const arr = [...leads]
    if (sortBy === '按优先级降序') {
      arr.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
    } else if (sortBy === '按意向分排序') {
      arr.sort((a, b) => b.intentScore - a.intentScore)
    } else if (sortBy === '按考试分数排序') {
      arr.sort((a, b) => b.score - a.score)
    }
    return arr
  }, [leads, sortBy])

  const totalProcessedPages = Math.ceil(processed.length / PAGE_SIZE)
  const processedPageData = processed.slice(processedPage * PAGE_SIZE, (processedPage + 1) * PAGE_SIZE)

  const moveToProcessed = (id: string, method: string = processMethod) => {
    const lead = leads.find((l) => l.id === id)
    if (!lead) return
    const now = new Date()
    const item: ProcessedItem = {
      id, name: lead.name, intentScore: lead.intentScore,
      profile: `${lead.province} / ${lead.subjectType} / ${lead.score}`,
      method, methodColor: PROCESS_STYLE[method] || PROCESS_STYLE['已电话联系'],
      time: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`,
      note: '',
    }
    setProcessed((prev) => [item, ...prev])
    setLeads((prev) => prev.filter((l) => l.id !== id))
    if (selected === id) setSelected(null)
    setProcessMenu(null)
    setProcessMenu(null)
  }

  const ignoreLead = (id: string) => {
    const lead = leads.find((l) => l.id === id)
    if (!lead) return
    const now = new Date()
    const item: ProcessedItem = {
      id, name: lead.name, intentScore: lead.intentScore,
      profile: `${lead.province} / ${lead.subjectType} / ${lead.score}`,
      method: '已忽略', methodColor: PROCESS_STYLE['已忽略'],
      time: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`,
      note: '已从待处理中移除',
    }
    setProcessed((prev) => [item, ...prev])
    setLeads((prev) => prev.filter((l) => l.id !== id))
    if (selected === id) setSelected(null)
    setProcessMenu(null)
  }

  const updatePriority = (id: string, p: Priority) => {
    setLeads((prev) => {
      const next = prev.map((l) => (l.id === id ? { ...l, priority: p } : l))
      if (sortBy === '按优先级降序') {
        next.sort((a, b) => PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority])
      }
      return next
    })
  }

  return (
    <div>
      {/* Page Toggle */}
      <div className="page-tabs" style={{ display: 'flex', gap: 2, background: '#f1f5f9', padding: 3, borderRadius: 10, width: 'fit-content', marginBottom: 14 }}>
        {(['pending', 'processed'] as PageTab[]).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setSelected(null); setShowPhone(null); setProcessMenu(null) }}
            style={{
              padding: '7px 22px', border: 'none', borderRadius: 8, cursor: 'pointer',
              fontSize: 13, fontWeight: tab === t ? 600 : 400, fontFamily: 'inherit',
              background: tab === t ? '#fff' : 'transparent',
              color: tab === t ? 'var(--color-brand-800)' : 'var(--color-text-secondary)',
              boxShadow: tab === t ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
              transition: 'all 0.15s',
            }}
          >
            {t === 'pending' ? '待处理线索' : '已处理线索'}
          </button>
        ))}
      </div>

      {tab === 'pending' ? (
        <>
          {/* Pending Leads Card */}
          <div className="card" style={{ padding: 0, marginBottom: 14 }}>
            <div style={{
              padding: '14px 18px', borderBottom: '1px solid var(--color-border)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 2px' }}>待处理线索</h2>
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                  共 <b style={{ color: 'var(--color-brand-800)' }}>{leads.length}</b> 条待处理
                </div>
              </div>
              {(() => {
                const sortIcon = {
                  '按优先级降序': <ArrowUpDown size={14} />,
                  '按意向分排序': <Flame size={14} />,
                  '按考试分数排序': <BarChart3 size={14} />,
                  '按时间最新': <Clock size={14} />,
                }[sortBy]
                return (
                  <button
                    onClick={() => setSortSheetOpen(true)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 6,
                      padding: '6px 12px', border: '1px solid var(--color-border)',
                      borderRadius: 6, fontSize: 12, fontFamily: 'inherit',
                      background: '#f8fafc', cursor: 'pointer',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {sortIcon}
                    {sortBy}
                  </button>
                )
              })()}
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
                      onClick={() => { setSelected(selected === lead.id ? null : lead.id); setProcessMenu(null) }}
                    >
                      <td style={{ padding: '8px 0', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => setPriorityTarget(lead.id)}
                          style={{
                            fontSize: 10, fontWeight: 600, padding: '3px 8px', borderRadius: 8,
                            border: '1px solid #e5e9f2', cursor: 'pointer', fontFamily: 'inherit',
                            background: PRIORITY_STYLE[lead.priority].bg,
                            color: PRIORITY_STYLE[lead.priority].color,
                          }}
                        >
                          {lead.priority}
                        </button>
                      </td>
                      <td style={{ padding: '10px 0' }}>
                        <span style={{ fontWeight: 600 }}>{lead.name}</span>
                        <span className="pill pill-blue" style={{ marginLeft: 8 }}>意向 {lead.intentScore}</span>
                      </td>
                      <td style={{ padding: '10px 0' }}>
                        <div style={{ fontWeight: 500 }}>{lead.province} / {lead.subjectType} / {lead.score}分</div>
                        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '2px 0' }}>{lead.major}</div>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {lead.concerns.map((c) => (
                            <span key={c} style={{ fontSize: 10, background: '#f1f5f9', padding: '1px 6px', borderRadius: 3, color: 'var(--color-text-secondary)' }}>{c}</span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: '10px 0', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', gap: isMobile ? 2 : 4, justifyContent: 'center', flexWrap: 'wrap' }}>
                          <button
                            onClick={() => setShowPhone(showPhone === lead.id ? null : lead.id)}
                            style={{
                              padding: isMobile ? '4px 6px' : '4px 10px', border: '1px solid #bfdbfe', background: '#fff',
                              borderRadius: 5, cursor: 'pointer', fontSize: 10, fontFamily: 'inherit',
                              color: 'var(--color-brand-800)', display: 'flex', alignItems: 'center', gap: 3,
                            }}
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                            {!isMobile && '电话'}
                          </button>
                          <button
                            onClick={() => {
                              alert(`跳转到与 ${lead.name} 的在线对话窗口`)
                            }}
                            style={{
                              padding: isMobile ? '4px 6px' : '4px 10px', border: '1px solid #bfdbfe', background: '#fff',
                              borderRadius: 5, cursor: 'pointer', fontSize: 10, fontFamily: 'inherit',
                              color: 'var(--color-brand-800)', display: 'flex', alignItems: 'center', gap: 3,
                            }}
                          >
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                            {!isMobile && '在线'}
                          </button>
                          {/* Process button */}
                          <button
                            onClick={() => setProcessMenu(processMenu === lead.id ? null : lead.id)}
                            style={{
                              padding: isMobile ? '4px 6px' : '4px 10px', background: '#22c55e', color: '#fff', border: 'none',
                              borderRadius: 5, cursor: 'pointer', fontSize: 10, fontFamily: 'inherit',
                              display: 'flex', alignItems: 'center', gap: 3,
                            }}
                          >
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                            {!isMobile && '已处理'}
                          </button>
                          <button
                            onClick={() => ignoreLead(lead.id)}
                            style={{
                              padding: isMobile ? '4px 6px' : '4px 10px', border: '1px solid #fee2e2', background: '#fff',
                              borderRadius: 5, cursor: 'pointer', fontSize: 10, fontFamily: 'inherit',
                              color: '#f5222d', display: 'flex', alignItems: 'center', gap: 3,
                            }}
                          >
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                            {!isMobile && '忽略'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {leads.length === 0 && (
                    <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 40 }}>暂无待处理线索</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Phone reveal bar */}
          {showPhone && (() => {
            const lead = leads.find((l) => l.id === showPhone)
            if (!lead) return null
            const formatted = lead.phone.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3')
            return (
              <div style={{
                background: '#fff', border: '1px solid var(--color-brand-800)', borderRadius: 10,
                padding: '14px 18px', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 12,
              }}>
                <div style={{ width: 36, height: 36, background: '#dbeafe', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>📞</div>
                <div>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>{lead.name} · 联系电话</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-brand-800)', letterSpacing: '0.04em' }}>{formatted}</div>
                </div>
                <button onClick={() => setShowPhone(null)} style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: '#9ba3b2', fontSize: 18 }}>×</button>
              </div>
            )
          })()}

          {/* Detail Panel */}
          {selectedLead && (
            <div className="card" style={{ marginBottom: 14, borderLeft: '3px solid var(--color-brand-800)', animation: 'page-enter 0.2s ease' }}>
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
                  <button
                    onClick={() => setProcessMenu(selectedLead.id)}
                    className="btn btn-sm"
                    style={{
                      background: '#22c55e', color: '#fff', border: 'none',
                      display: 'flex', alignItems: 'center', gap: 4, fontSize: 11,
                    }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                    已处理
                  </button>
                  <button
                    onClick={() => ignoreLead(selectedLead.id)}
                    className="btn btn-sm"
                    style={{
                      display: 'flex', alignItems: 'center', gap: 3, fontSize: 11,
                      border: '1px solid #fee2e2', color: '#f5222d', background: '#fff',
                    }}
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                    忽略
                  </button>
                </div>
              </div>
              <div style={{ display: 'flex', gap: isMobile ? 12 : 18, flexDirection: isMobile ? 'column' : 'row' }}>
                <div style={{ flex: isMobile ? undefined : 1.2 }}>
                  <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>{selectedLead.detail.reason}</div>
                </div>
                <div style={{ flex: isMobile ? undefined : 0.8, borderLeft: isMobile ? 'none' : '1px solid var(--color-border)', borderTop: isMobile ? '1px solid var(--color-border)' : 'none', paddingLeft: isMobile ? 0 : 16, paddingTop: isMobile ? 10 : 0 }}>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 2 }}>学生画像</div>
                  <div style={{ fontSize: 12, fontWeight: 500 }}>{selectedLead.detail.profile}</div>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 10, marginBottom: 2 }}>核心关注</div>
                  <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{selectedLead.detail.coreInterests}</div>
                </div>
                <div style={{ flex: isMobile ? undefined : 0.8, borderLeft: isMobile ? 'none' : '1px solid var(--color-border)', borderTop: isMobile ? '1px solid var(--color-border)' : 'none', paddingLeft: isMobile ? 0 : 16, paddingTop: isMobile ? 10 : 0 }}>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginBottom: 2 }}>推荐材料</div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', lineHeight: 1.7 }}>{selectedLead.detail.materials}</div>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        /* Processed Page */
        <div className="card" style={{ padding: 0 }}>
          <div style={{
            padding: '12px 16px', borderBottom: '1px solid var(--color-border)',
            background: '#f8fafc',
          }}>
            <b style={{ fontSize: 13 }}>已处理线索</b>
            <span style={{ fontSize: 10, color: 'var(--color-text-muted)', marginLeft: 8 }}>共 {processed.length} 条记录</span>
          </div>
          {processed.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 40, fontSize: 13 }}>
              暂无已处理记录
            </div>
          ) : (
            <>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>学生</th><th>画像</th><th>处理方式</th><th>处理时间</th><th>备注</th>
                    </tr>
                  </thead>
                  <tbody>
                    {processedPageData.map((p) => (
                      <tr key={p.id}>
                        <td>
                          <span style={{ fontWeight: 500 }}>{p.name}</span>
                          <span style={{ color: 'var(--color-text-muted)', fontSize: 11, marginLeft: 6 }}>意向 {p.intentScore}</span>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{p.profile}</td>
                        <td>
                          <span style={{ background: p.methodColor.bg, color: p.methodColor.color, padding: '2px 8px', borderRadius: 8, fontSize: 10 }}>{p.method}</span>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{p.time}</td>
                        <td style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{p.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Pagination */}
              {totalProcessedPages > 1 && (
                <div style={{
                  padding: '10px 16px', borderTop: '1px solid var(--color-border)',
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  fontSize: 12, background: '#fafafa',
                }}>
                  <span style={{ color: 'var(--color-text-muted)' }}>
                    第 {processedPage + 1}/{totalProcessedPages} 页 · 共 {processed.length} 条
                  </span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button className="btn btn-sm btn-secondary" disabled={processedPage === 0} onClick={() => setProcessedPage(0)}>首页</button>
                    <button className="btn btn-sm btn-secondary" disabled={processedPage === 0} onClick={() => setProcessedPage((p) => p - 1)}>上一页</button>
                    <button className="btn btn-sm btn-secondary" disabled={processedPage >= totalProcessedPages - 1} onClick={() => setProcessedPage((p) => p + 1)}>下一页</button>
                    <button className="btn btn-sm btn-secondary" disabled={processedPage >= totalProcessedPages - 1} onClick={() => setProcessedPage(totalProcessedPages - 1)}>末页</button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Bottom Sheet: priority selector */}
      <BottomSheet
        open={!!priorityTarget}
        title="更改优先级"
        onClose={() => setPriorityTarget(null)}
      >
        {(['P0', 'P1', 'P2', 'P3'] as Priority[]).map((p) => {
          const lead = leads.find((l) => l.id === priorityTarget)
          const isActive = lead?.priority === p
          return (
            <button
              key={p}
              className="bs-row"
              onClick={() => {
                if (priorityTarget) updatePriority(priorityTarget, p)
                setPriorityTarget(null)
              }}
              style={isActive ? { background: '#f8fafc' } : undefined}
            >
              <div className="bs-row-icon" style={{ background: PRIORITY_STYLE[p].bg, color: PRIORITY_STYLE[p].color, fontWeight: 700 }}>
                {p}
              </div>
              <span className="bs-row-text" style={isActive ? { fontWeight: 600 } : undefined}>{p}</span>
              {isActive && <span style={{ color: 'var(--color-brand-800)', fontWeight: 600, fontSize: 18 }}>✓</span>}
            </button>
          )
        })}
        <button className="bs-cancel" onClick={() => setPriorityTarget(null)}>取消</button>
      </BottomSheet>

      {/* Bottom Sheet: sort selector */}
      <BottomSheet
        open={sortSheetOpen}
        title="排序方式"
        onClose={() => setSortSheetOpen(false)}
      >
        {[
          { label: '按优先级降序', icon: <ArrowUpDown size={20} />, bg: '#fee2e2', color: '#991b1b' },
          { label: '按意向分排序', icon: <Flame size={20} />, bg: '#fef3c7', color: '#92400e' },
          { label: '按考试分数排序', icon: <BarChart3 size={20} />, bg: '#dbeafe', color: '#1e40af' },
          { label: '按时间最新', icon: <Clock size={20} />, bg: '#f3e8ff', color: '#7c3aed' },
        ].map((opt) => {
          const isActive = sortBy === opt.label
          return (
            <button
              key={opt.label}
              className="bs-row"
              onClick={() => { setSortBy(opt.label); setSortSheetOpen(false) }}
              style={isActive ? { background: '#f0f7ff' } : undefined}
            >
              <div className="bs-row-icon" style={{ background: opt.bg, color: opt.color }}>
                {opt.icon}
              </div>
              <span className="bs-row-text" style={isActive ? { fontWeight: 600, color: 'var(--color-brand-800)' } : undefined}>
                {opt.label}
              </span>
              {isActive && <span style={{ color: 'var(--color-brand-800)', fontWeight: 600, fontSize: 18 }}>✓</span>}
            </button>
          )
        })}
        <button className="bs-cancel" onClick={() => setSortSheetOpen(false)}>取消</button>
      </BottomSheet>

      {/* Bottom Sheet: process method selector */}
      <BottomSheet
        open={!!processMenu}
        title="选择处理方式"
        onClose={() => setProcessMenu(null)}
      >
        <button className="bs-row" onClick={() => {
          const lead = leads.find((l) => l.id === processMenu)
          if (lead) moveToProcessed(lead.id, '已电话联系')
        }}>
          <div className="bs-row-icon" style={{ background: '#dcfce7', color: '#166534' }}>
            <Phone size={20} />
          </div>
          <span className="bs-row-text">已电话联系</span>
          <svg className="bs-row-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
        <button className="bs-row" onClick={() => {
          const lead = leads.find((l) => l.id === processMenu)
          if (lead) moveToProcessed(lead.id, '在线对话')
        }}>
          <div className="bs-row-icon" style={{ background: '#dbeafe', color: '#1e40af' }}>
            <MessageCircle size={20} />
          </div>
          <span className="bs-row-text">在线对话</span>
          <svg className="bs-row-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
        <button className="bs-row" onClick={() => {
          const lead = leads.find((l) => l.id === processMenu)
          if (lead) moveToProcessed(lead.id, '已发材料')
        }}>
          <div className="bs-row-icon" style={{ background: '#fef3c7', color: '#92400e' }}>
            <FileText size={20} />
          </div>
          <span className="bs-row-text">已发材料</span>
          <svg className="bs-row-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
        <button className="bs-cancel" onClick={() => setProcessMenu(null)}>取消</button>
      </BottomSheet>
    </div>
  )
}
