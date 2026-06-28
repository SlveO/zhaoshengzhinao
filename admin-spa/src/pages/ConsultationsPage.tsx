import { useEffect, useState } from 'react'
import { ListFilter, Calendar, X } from 'lucide-react'
import api from '../api/client'
import BottomSheet from '../components/BottomSheet'

interface ConsultRow {
  session_id: string
  session_string: string
  student_name: string
  province: string
  subjects: string
  score: number
  rank: number | null
  intent_majors: string[]
  consult_summary: string
  consult_started_at: string | null
  follow_status: string
  follow_note: string
}

interface ConsultDetail {
  session: ConsultRow & {
    focus_points: string[]
    consult_started_at: string | null
    followed_at: string | null
  }
  messages: { id: string; role: string; content: string; created_at: string }[]
}

const PAGE_SIZE = 10

export default function ConsultationsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [period, setPeriod] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const [statusSheetOpen, setStatusSheetOpen] = useState(false)
  const [periodSheetOpen, setPeriodSheetOpen] = useState(false)
  const [rows, setRows] = useState<ConsultRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<ConsultDetail | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [followNote, setFollowNote] = useState('')
  const [followStatusUpdating, setFollowStatusUpdating] = useState(false)
  const [noteSaving, setNoteSaving] = useState(false)
  const [summaryDraft, setSummaryDraft] = useState('')
  const [summaryEditing, setSummaryEditing] = useState(false)
  const [summarySaving, setSummarySaving] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { page: page + 1, page_size: PAGE_SIZE }
      if (statusFilter) params.status = statusFilter
      if (period) params.period = period
      if (search) params.search = search
      const res = await api.get('/admin/consultations', { params })
      setRows(res.data?.data || [])
      setTotal(res.data?.total || 0)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [page, statusFilter, period, search])

  async function openDetail(row: ConsultRow) {
    setDetailOpen(true)
    setDetailLoading(true)
    setSelected(null)
    try {
      const res = await api.get(`/admin/consultations/${row.session_id}`)
      setSelected(res.data)
      setFollowNote(res.data?.session?.follow_note || '')
      setSummaryDraft(res.data?.session?.consult_summary || '')
      setSummaryEditing(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载详情失败')
    } finally {
      setDetailLoading(false)
    }
  }

  async function updateFollowStatus(status: string) {
    if (!selected) return
    setFollowStatusUpdating(true)
    try {
      await api.patch(`/admin/consultations/${selected.session.session_id}/follow-status`, {
        status,
        note: followNote,
      })
      // Refresh detail
      const res = await api.get(`/admin/consultations/${selected.session.session_id}`)
      setSelected(res.data)
      load()  // Refresh list
    } catch (e) {
      setError(e instanceof Error ? e.message : '更新失败')
    } finally {
      setFollowStatusUpdating(false)
    }
  }

  async function regenerateSummary() {
    if (!selected || regenerating) return
    setRegenerating(true)
    setToast(null)
    try {
      await api.post(`/admin/consultations/${selected.session.session_id}/regenerate-summary`)
      const res = await api.get(`/admin/consultations/${selected.session.session_id}`)
      setSelected(res.data)
      setSummaryDraft(res.data?.session?.consult_summary || '')
      setToast({ msg: '咨询摘要已重新生成', type: 'success' })
    } catch (e) {
      const msg = e instanceof Error ? e.message : '重新生成摘要失败'
      setError(msg)
      setToast({ msg, type: 'error' })
    } finally {
      setRegenerating(false)
      // 自动 3 秒后清掉 toast
      setTimeout(() => setToast(null), 3000)
    }
  }

  async function saveSummary() {
    if (!selected || summarySaving) return
    setSummarySaving(true)
    setToast(null)
    try {
      await api.patch(`/admin/consultations/${selected.session.session_id}/summary`, { summary: summaryDraft })
      const res = await api.get(`/admin/consultations/${selected.session.session_id}`)
      setSelected(res.data)
      setSummaryEditing(false)
      setToast({ msg: '咨询摘要已保存', type: 'success' })
      load()
    } catch (e) {
      setToast({ msg: e instanceof Error ? e.message : '保存摘要失败', type: 'error' })
    } finally {
      setSummarySaving(false)
      setTimeout(() => setToast(null), 3000)
    }
  }

  async function saveFollowNote() {
    if (!selected || noteSaving) return
    setNoteSaving(true)
    setToast(null)
    try {
      await api.patch(`/admin/consultations/${selected.session.session_id}/follow-note`, { note: followNote })
      const res = await api.get(`/admin/consultations/${selected.session.session_id}`)
      setSelected(res.data)
      setToast({ msg: '跟进备注已保存', type: 'success' })
      load()
    } catch (e) {
      setToast({ msg: e instanceof Error ? e.message : '保存备注失败', type: 'error' })
    } finally {
      setNoteSaving(false)
      setTimeout(() => setToast(null), 3000)
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div>
      <div className="search-bar">
        <button
          onClick={() => setStatusSheetOpen(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '7px 12px', border: '1px solid var(--color-border)',
            borderRadius: 8, fontSize: 12, fontFamily: 'inherit',
            background: '#f8fafc', cursor: 'pointer',
            color: statusFilter ? 'var(--color-brand-800)' : 'var(--color-text-secondary)',
            fontWeight: statusFilter ? 600 : 400,
          }}
        >
          <ListFilter size={14} />
          {statusFilter === 'pending' ? '待跟进' :
           statusFilter === 'processed' ? '已处理' :
           statusFilter === 'ignored' ? '已忽略' :
           statusFilter === 'no_consult' ? '未咨询' : '全部状态'}
        </button>
        <button
          onClick={() => setPeriodSheetOpen(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 5,
            padding: '7px 12px', border: '1px solid var(--color-border)',
            borderRadius: 8, fontSize: 12, fontFamily: 'inherit',
            background: '#f8fafc', cursor: 'pointer',
            color: period ? 'var(--color-brand-800)' : 'var(--color-text-secondary)',
            fontWeight: period ? 600 : 400,
          }}
        >
          <Calendar size={14} />
          {period === 'today' ? '今天' :
           period === '7d' ? '近7天' :
           period === '30d' ? '近30天' : '全部时间'}
        </button>
        <input
          type="text" placeholder="搜索学生或摘要…"
          value={search} onChange={(e) => { setSearch(e.target.value); setPage(0) }}
        />
      </div>

      {error && (
        <div style={{ padding: 12, color: 'var(--color-danger)', fontSize: 13, marginBottom: 8 }}>
          {error}
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>学生</th>
                <th>省份</th>
                <th>选科</th>
                <th>分数</th>
                <th>位次</th>
                <th>咨询摘要</th>
                <th>咨询时间</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} style={{ textAlign: 'center', padding: 32, color: 'var(--color-text-muted)' }}>加载中…</td></tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 32 }}>
                    暂无咨询记录
                  </td>
                </tr>
              ) : rows.map((s) => (
                <tr key={s.session_id} style={{ cursor: 'pointer' }} onClick={() => openDetail(s)}>
                  <td><span style={{ fontWeight: 500 }}>{s.student_name}</span></td>
                  <td>{s.province || '—'}</td>
                  <td>{s.subjects || '—'}</td>
                  <td>{s.score || '—'}</td>
                  <td>{s.rank ?? '—'}</td>
                  <td style={{ maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {s.consult_summary || '（无摘要）'}
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                    {s.consult_started_at ? formatDateTime(s.consult_started_at) : '—'}
                  </td>
                  <td><StatusPill status={s.follow_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="pagination">
        <span>共 {total} 条</span>
        <button className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => setPage(0)}>首页</button>
        <button className="btn btn-secondary btn-sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>上一页</button>
        <span>第 {page + 1}/{totalPages || 1} 页</span>
        <button className="btn btn-secondary btn-sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>下一页</button>
      </div>

      {/* Status Filter Sheet */}
      <BottomSheet open={statusSheetOpen} title="咨询状态" onClose={() => setStatusSheetOpen(false)}>
        {[
          { label: '全部状态', value: '' },
          { label: '待跟进', value: 'pending' },
          { label: '已处理', value: 'processed' },
          { label: '已忽略', value: 'ignored' },
          { label: '未咨询', value: 'no_consult' },
        ].map((opt) => {
          const isActive = statusFilter === opt.value
          return (
            <button key={opt.value} className="bs-row"
              onClick={() => { setStatusFilter(opt.value); setPage(0); setStatusSheetOpen(false) }}
              style={isActive ? { background: '#f8fafc' } : undefined}>
              <span className="bs-row-text" style={isActive ? { fontWeight: 600 } : undefined}>{opt.label}</span>
              {isActive && <span style={{ color: 'var(--color-brand-800)', fontWeight: 600, fontSize: 18 }}>✓</span>}
            </button>
          )
        })}
        <button className="bs-cancel" onClick={() => setStatusSheetOpen(false)}>取消</button>
      </BottomSheet>

      {/* Period Filter Sheet */}
      <BottomSheet open={periodSheetOpen} title="时间范围" onClose={() => setPeriodSheetOpen(false)}>
        {[
          { label: '全部时间', value: '' },
          { label: '今天', value: 'today' },
          { label: '近7天', value: '7d' },
          { label: '近30天', value: '30d' },
        ].map((opt) => {
          const isActive = period === opt.value
          return (
            <button key={opt.value} className="bs-row"
              onClick={() => { setPeriod(opt.value); setPage(0); setPeriodSheetOpen(false) }}
              style={isActive ? { background: '#f8fafc' } : undefined}>
              <div className="bs-row-icon" style={{ background: '#dbeafe', color: '#1e40af' }}>
                <Calendar size={20} />
              </div>
              <span className="bs-row-text" style={isActive ? { fontWeight: 600 } : undefined}>{opt.label}</span>
              {isActive && <span style={{ color: 'var(--color-brand-800)', fontWeight: 600, fontSize: 18 }}>✓</span>}
            </button>
          )
        })}
        <button className="bs-cancel" onClick={() => setPeriodSheetOpen(false)}>取消</button>
      </BottomSheet>

      {/* Detail Drawer */}
      {detailOpen && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 200,
          display: 'flex', justifyContent: 'flex-end',
        }} onClick={() => setDetailOpen(false)}>
          <div style={{
            width: '100%', maxWidth: 560, background: '#fff', height: '100%',
            overflowY: 'auto', padding: 24, boxSizing: 'border-box',
          }} onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>咨询详情</h3>
              <button onClick={() => setDetailOpen(false)} style={{
                border: 'none', background: 'none', cursor: 'pointer', padding: 4,
              }}><X size={20} /></button>
            </div>

            {detailLoading ? (
              <div style={{ textAlign: 'center', color: '#888', padding: 24 }}>加载中…</div>
            ) : selected ? (
              <>
                {/* Basic info */}
                <div style={{ marginBottom: 16, padding: 12, background: '#f8fafc', borderRadius: 8 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 13 }}>
                    <div><span style={{ color: '#888' }}>学生：</span>{selected.session.student_name}</div>
                    <div><span style={{ color: '#888' }}>省份：</span>{selected.session.province || '—'}</div>
                    <div><span style={{ color: '#888' }}>选科：</span>{selected.session.subjects || '—'}</div>
                    <div><span style={{ color: '#888' }}>分数：</span>{selected.session.score || '—'}</div>
                    <div><span style={{ color: '#888' }}>位次：</span>{selected.session.rank ?? '—'}</div>
                    <div><span style={{ color: '#888' }}>意向专业：</span>{selected.session.intent_majors?.join('、') || '—'}</div>
                    <div><span style={{ color: '#888' }}>关注点：</span>{selected.session.focus_points?.join('、') || '—'}</div>
                  </div>
                </div>

                {/* 已保存的跟进备注（顶部展示，方便老师快速查看） */}
                {selected.session.follow_note && (
                  <div style={{ marginBottom: 16, padding: 10, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8 }}>
                    <div style={{ fontSize: 11, color: '#92400e', marginBottom: 4, fontWeight: 600 }}>跟进备注</div>
                    <div style={{ fontSize: 13, color: '#78350f', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                      {selected.session.follow_note}
                    </div>
                    {selected.session.followed_at && (
                      <div style={{ fontSize: 11, color: '#a16207', marginTop: 6 }}>
                        更新于 {formatDateTime(selected.session.followed_at)}
                      </div>
                    )}
                  </div>
                )}

                {/* Consultation summary */}
                <div style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <h4 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>咨询摘要</h4>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        onClick={() => {
                          if (summaryEditing) {
                            setSummaryEditing(false)
                            setSummaryDraft(selected.session.consult_summary || '')
                          } else {
                            setSummaryEditing(true)
                            setSummaryDraft(selected.session.consult_summary || '')
                          }
                        }}
                        disabled={regenerating || summarySaving}
                        style={{
                          border: '1px solid var(--color-border)',
                          background: summaryEditing ? '#eff6ff' : '#fff',
                          padding: '4px 12px',
                          borderRadius: 6,
                          fontSize: 12,
                          cursor: (regenerating || summarySaving) ? 'not-allowed' : 'pointer',
                          color: summaryEditing ? '#2563eb' : 'inherit',
                        }}
                      >
                        {summaryEditing ? '取消编辑' : '编辑'}
                      </button>
                      <button
                        onClick={regenerateSummary}
                        disabled={regenerating || summaryEditing}
                        style={{
                          border: '1px solid var(--color-border)',
                          background: regenerating ? '#f3f4f6' : '#fff',
                          padding: '4px 12px',
                          borderRadius: 6,
                          fontSize: 12,
                          cursor: regenerating ? 'not-allowed' : 'pointer',
                          color: regenerating ? '#9ca3af' : 'inherit',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                        }}
                      >
                        {regenerating && (
                          <span
                            style={{
                              display: 'inline-block',
                              width: 12,
                              height: 12,
                              border: '2px solid #d1d5db',
                              borderTopColor: '#2563eb',
                              borderRadius: '50%',
                              animation: 'spin 0.8s linear infinite',
                            }}
                          />
                        )}
                        {regenerating ? '生成中...' : '重新生成'}
                      </button>
                    </div>
                  </div>
                  {regenerating && (
                    <div style={{
                      marginBottom: 8, padding: '6px 10px', background: '#eff6ff',
                      border: '1px solid #bfdbfe', borderRadius: 6,
                      fontSize: 12, color: '#1e40af',
                    }}>
                      正在调用 AI 重新生成咨询摘要，请稍候…
                    </div>
                  )}
                  {toast && (
                    <div style={{
                      marginBottom: 8, padding: '6px 10px',
                      background: toast.type === 'success' ? '#ecfdf5' : '#fef2f2',
                      border: `1px solid ${toast.type === 'success' ? '#a7f3d0' : '#fecaca'}`,
                      borderRadius: 6,
                      fontSize: 12,
                      color: toast.type === 'success' ? '#065f46' : '#991b1b',
                    }}>
                      {toast.msg}
                    </div>
                  )}
                  {summaryEditing ? (
                    <div>
                      <textarea
                        value={summaryDraft}
                        onChange={(e) => setSummaryDraft(e.target.value)}
                        placeholder="可人工编辑咨询摘要…"
                        style={{
                          width: '100%', minHeight: 120, padding: 8,
                          border: '1px solid var(--color-border)', borderRadius: 6,
                          fontSize: 13, fontFamily: 'inherit', resize: 'vertical',
                          boxSizing: 'border-box', lineHeight: 1.6,
                        }}
                      />
                      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                        <button
                          onClick={saveSummary}
                          disabled={summarySaving}
                          style={{
                            padding: '6px 16px', border: 'none', borderRadius: 6,
                            background: summarySaving ? '#9ca3af' : '#2563eb',
                            color: '#fff', fontSize: 12, cursor: summarySaving ? 'not-allowed' : 'pointer',
                          }}
                        >
                          {summarySaving ? '保存中...' : '保存摘要'}
                        </button>
                        <button
                          onClick={() => {
                            setSummaryEditing(false)
                            setSummaryDraft(selected.session.consult_summary || '')
                          }}
                          disabled={summarySaving}
                          style={{
                            padding: '6px 16px', border: '1px solid var(--color-border)',
                            borderRadius: 6, background: '#fff', color: '#666',
                            fontSize: 12, cursor: 'pointer',
                          }}
                        >
                          取消
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: 12, background: '#f9fafb', borderRadius: 8, fontSize: 13, lineHeight: 1.6, color: '#333', whiteSpace: 'pre-wrap' }}>
                      {selected.session.consult_summary || '（暂无摘要，需对话 4 轮以上自动生成，或点击"编辑"手动填写）'}
                    </div>
                  )}
                </div>

                {/* Chat messages */}
                <div style={{ marginBottom: 16 }}>
                  <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>对话记录</h4>
                  <div style={{ maxHeight: 320, overflowY: 'auto', padding: 8, background: '#f9fafb', borderRadius: 8 }}>
                    {selected.messages.length === 0 ? (
                      <div style={{ textAlign: 'center', color: '#888', padding: 16 }}>暂无对话记录</div>
                    ) : selected.messages.map((m) => (
                      <div key={m.id} style={{
                        marginBottom: 8, padding: 8, borderRadius: 6,
                        background: m.role === 'user' ? '#dbeafe' : '#fff',
                        fontSize: 13,
                      }}>
                        <div style={{ fontSize: 11, color: '#888', marginBottom: 2 }}>
                          {m.role === 'user' ? '学生' : 'AI'} · {formatDateTime(m.created_at)}
                        </div>
                        <div>{m.content}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Follow-up */}
                <div>
                  <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>跟进操作</h4>
                  <textarea
                    value={followNote}
                    onChange={(e) => setFollowNote(e.target.value)}
                    placeholder="添加跟进备注…"
                    style={{
                      width: '100%', minHeight: 80, padding: 8,
                      border: '1px solid var(--color-border)', borderRadius: 6,
                      fontSize: 13, fontFamily: 'inherit', resize: 'vertical', boxSizing: 'border-box',
                    }}
                  />
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button
                      onClick={saveFollowNote}
                      disabled={noteSaving}
                      style={{
                        padding: '8px 14px', border: '1px solid var(--color-border)', borderRadius: 6,
                        background: noteSaving ? '#f3f4f6' : '#fff', color: '#2563eb',
                        fontSize: 13, cursor: noteSaving ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {noteSaving ? '保存中...' : '保存备注'}
                    </button>
                    <div style={{ flex: 1 }} />
                    <button
                      onClick={() => updateFollowStatus('processed')}
                      disabled={followStatusUpdating}
                      style={{
                        padding: '8px 14px', border: 'none', borderRadius: 6,
                        background: '#16a34a', color: '#fff', fontSize: 13, cursor: 'pointer',
                      }}
                    >标记已处理</button>
                    <button
                      onClick={() => updateFollowStatus('ignored')}
                      disabled={followStatusUpdating}
                      style={{
                        padding: '8px 14px', border: 'none', borderRadius: 6,
                        background: '#f3f4f6', color: '#666', fontSize: 13, cursor: 'pointer',
                      }}
                    >忽略</button>
                  </div>
                </div>
              </>
            ) : (
              <div style={{ textAlign: 'center', color: '#888', padding: 24 }}>加载失败</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function StatusPill({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    pending: { label: '待跟进', cls: 'pill-amber' },
    processed: { label: '已处理', cls: 'pill-green' },
    ignored: { label: '已忽略', cls: 'pill' },
  }
  const cfg = map[status] || map.pending
  return <span className={`pill ${cfg.cls}`}>{cfg.label}</span>
}

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso)
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mm = String(d.getMinutes()).padStart(2, '0')
    return `${m}-${day} ${hh}:${mm}`
  } catch {
    return iso
  }
}
