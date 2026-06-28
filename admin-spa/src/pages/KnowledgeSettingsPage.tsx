import { useEffect, useRef, useState } from 'react'
import api from '../api/client'
import type { DocumentItem } from '../types'
import StatusCard from '../components/StatusCard'
import Modal from '../components/Modal'

const PAGE_SIZE = 6

interface ReindexProgress {
  status: 'idle' | 'running' | 'completed' | 'failed'
  total: number
  done: number
  percent: number
  started_at: string | null
  finished_at: string | null
  error: string | null
  triggered_by: string
}

interface IndexStatusResp {
  total_docs: number
  indexed_docs: number
  pending_docs: number
  reindex: ReindexProgress
}

const POLL_INTERVAL = 1500
const TYPE_NAMES: Record<string, string> = {
  admission_score: '录取分数', curriculum: '课程信息', employment: '就业数据', campus_life: '校园生活',
}

export default function KnowledgeSettingsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [uploadType, setUploadType] = useState('admission_score')
  const [page, setPage] = useState(0)
  const [deleteTarget, setDeleteTarget] = useState<DocumentItem | null>(null)
  const [message, setMessage] = useState('')
  const [reindexProgress, setReindexProgress] = useState<ReindexProgress | null>(null)
  const [indexing, setIndexing] = useState(false)
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchDocs = () => {
    api.get<{ documents: DocumentItem[] }>('/admin/knowledge/documents')
      .then((r) => setDocs(r.data.documents ?? []))
      .catch((e) => {
        setError(e?.message || '获取知识库文档失败')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchDocs() }, [])

  const pollIndexStatus = () => {
    api.get<IndexStatusResp>('/admin/knowledge/index-status')
      .then((r) => {
        setReindexProgress(r.data.reindex)
        if (r.data.reindex.status === 'running') {
          pollTimer.current = setTimeout(pollIndexStatus, POLL_INTERVAL)
        } else {
          setIndexing(false)
          if (r.data.reindex.status === 'completed' || r.data.reindex.status === 'failed') {
            fetchDocs()
          }
        }
      })
      .catch(() => {
        pollTimer.current = setTimeout(pollIndexStatus, POLL_INTERVAL * 2)
      })
  }

  // 挂载时检查是否有正在进行的索引
  useEffect(() => {
    api.get<IndexStatusResp>('/admin/knowledge/index-status')
      .then((r) => {
        setReindexProgress(r.data.reindex)
        if (r.data.reindex.status === 'running') {
          setIndexing(true)
          pollTimer.current = setTimeout(pollIndexStatus, POLL_INTERVAL)
        }
      })
      .catch(() => {})
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current)
    }
  }, [])

  const filtered = docs.filter((d) => {
    if (search && !d.title.toLowerCase().includes(search.toLowerCase())) return false
    if (typeFilter && d.data_type !== typeFilter) return false
    return true
  })
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageDocs = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await api.delete(`/admin/knowledge/documents/${deleteTarget.id}`)
      setDocs((prev) => prev.filter((d) => d.id !== deleteTarget.id))
      setMessage('文档已删除')
      setDeleteTarget(null)
    } catch {
      setMessage('删除失败')
    }
  }

  const handleUploadClick = () => {
    // 上传功能暂时关闭，引导联系技术人员
    setMessage('文档上传功能暂时关闭，如需上传请联系技术人员')
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('data_type', uploadType)
    try {
      await api.post('/admin/knowledge/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setMessage('文档上传成功')
      fetchDocs()
    } catch {
      setMessage('上传失败')
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleReindex = async () => {
    if (indexing) return
    setIndexing(true)
    try {
      await api.post('/admin/knowledge/reindex')
      setMessage('重新索引已触发，正在后台处理…')
      pollTimer.current = setTimeout(pollIndexStatus, POLL_INTERVAL)
    } catch {
      setMessage('重新索引失败')
      setIndexing(false)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>索引状态：</span>
        <span className="pill green">
          已索引 {docs.filter((d) => d.indexed_at).length} / 共 {docs.length}
        </span>
        <button className="btn btn-secondary btn-sm" onClick={handleReindex} disabled={indexing}>
          {indexing ? '索引中…' : '重新索引'}
        </button>
      </div>

      {reindexProgress && reindexProgress.status !== 'idle' && (
        <ReindexProgressBar progress={reindexProgress} />
      )}

      <div className="search-bar">
        <input type="text" placeholder="搜索文档标题…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0) }} />
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(0) }} style={{ padding: '7px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--surface)' }}>
          <option value="">全部类型</option>
          {Object.entries(TYPE_NAMES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select value={uploadType} onChange={(e) => setUploadType(e.target.value)} style={{ padding: '7px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--surface)' }}>
          {Object.entries(TYPE_NAMES).map(([k, v]) => <option key={k} value={k}>上传为：{v}</option>)}
        </select>
        <input ref={fileInputRef} type="file" accept=".json,.csv,.xlsx,.xls,.txt" style={{ display: 'none' }} onChange={handleFileChange} disabled />
        <button className="btn btn-primary btn-sm" onClick={handleUploadClick} title="上传功能暂时关闭，请联系技术人员">上传文档</button>
      </div>

      {message && (
        <div className="view-status loading" style={{ marginBottom: 12 }}>
          {message}
          <button className="btn btn-sm btn-secondary" style={{ marginLeft: 8 }} onClick={() => setMessage('')}>×</button>
        </div>
      )}

      <StatusCard loading={loading} error={error}>
        <div className="card" style={{ padding: 0 }}>
          <div className="table-wrap">
            <table>
              <thead><tr><th>文档标题</th><th>类型</th><th>年份</th><th>索引状态</th><th>索引时间</th><th>操作</th></tr></thead>
              <tbody>
                {pageDocs.map((doc) => (
                  <tr key={doc.id}>
                    <td style={{ fontWeight: 500 }}>{doc.title}</td>
                    <td>{TYPE_NAMES[doc.data_type] || doc.data_type}</td>
                    <td>{doc.year || '—'}</td>
                    <td>{doc.indexed_at ? <span className="pill green">已索引</span> : <span className="pill amber">待索引</span>}</td>
                    <td style={{ fontSize: 12, color: 'var(--muted)' }}>{doc.indexed_at ? new Date(doc.indexed_at).toLocaleDateString('zh-CN') : '—'}</td>
                    <td><button className="btn btn-secondary btn-sm" onClick={() => setDeleteTarget(doc)}>删除</button></td>
                  </tr>
                ))}
                {pageDocs.length === 0 && (
                  <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--muted)', padding: 24 }}>暂无文档</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        <div className="pagination">
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(0)} disabled={page === 0}>首页</button>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => p - 1)} disabled={page === 0}>上一页</button>
          <span>第 {page + 1} / {totalPages || 1} 页（共 {filtered.length} 条）</span>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages - 1}>下一页</button>
          <button className="btn btn-secondary btn-sm" onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1}>末页</button>
        </div>
      </StatusCard>

      <Modal
        open={!!deleteTarget}
        title="确认删除"
        message={`确定要删除文档 "${deleteTarget?.title || ''}" 吗？此操作不可撤销。`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}

function ReindexProgressBar({ progress }: { progress: ReindexProgress }) {
  const { status, total, done, percent, error } = progress
  const bg = status === 'running' ? '#eff6ff' : status === 'completed' ? '#f0fdf4' : status === 'failed' ? '#fef2f2' : '#f9fafb'
  const color = status === 'running' ? '#2563eb' : status === 'completed' ? '#16a34a' : status === 'failed' ? '#dc2626' : '#666'
  const label =
    status === 'running' ? `正在重建索引 (${done}/${total})`
    : status === 'completed' ? `索引完成 (${total} 条)`
    : status === 'failed' ? `索引失败: ${error || '未知错误'}`
    : ''
  return (
    <div style={{ marginBottom: 12, padding: '8px 12px', background: bg, border: `1px solid ${color}33`, borderRadius: 4, fontSize: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ color, fontWeight: 500 }}>
          {status === 'running' && '⚙ '}{status === 'completed' && '✓ '}{status === 'failed' && '✗ '}
          {label}
        </span>
        {status === 'running' && <span style={{ color }}>{percent}%</span>}
      </div>
      {status === 'running' && (
        <div style={{ background: '#e5e7eb', height: 6, borderRadius: 2, overflow: 'hidden' }}>
          <div style={{ width: `${percent}%`, height: '100%', background: color, transition: 'width 0.3s ease' }} />
        </div>
      )}
    </div>
  )
}
