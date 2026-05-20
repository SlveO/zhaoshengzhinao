import { useEffect, useState } from 'react'
import api from '../api/client'
import type { DocumentItem } from '../types'
import StatusCard from '../components/StatusCard'
import Modal from '../components/Modal'

const PAGE_SIZE = 6
const TYPE_NAMES: Record<string, string> = {
  admission_score: '录取分数', curriculum: '课程信息', employment: '就业数据', campus_life: '校园生活',
}

export default function KnowledgeSettingsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [page, setPage] = useState(0)
  const [deleteTarget, setDeleteTarget] = useState<DocumentItem | null>(null)
  const [message, setMessage] = useState('')

  const fetchDocs = () => {
    api.get<{ documents: DocumentItem[] }>('/admin/knowledge/documents')
      .then((r) => setDocs(r.data.documents))
      .catch((e) => setError(e?.message || '获取知识库文档失败'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchDocs() }, [])

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

  const handleUpload = () => {
    const newDoc: DocumentItem = {
      id: 'd' + Date.now(),
      title: '新上传文档_' + new Date().toLocaleDateString('zh-CN'),
      data_type: 'admission_score',
      year: 2026,
      indexed_at: new Date().toISOString(),
    }
    setDocs((prev) => [newDoc, ...prev])
    setMessage('文档上传成功')
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>索引状态：</span>
        <span className="pill green">
          已索引 {docs.filter((d) => d.indexed_at).length} / 共 {docs.length}
        </span>
        <button className="btn btn-secondary btn-sm">重新索引</button>
      </div>

      <div className="search-bar">
        <input type="text" placeholder="搜索文档标题…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0) }} />
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(0) }} style={{ padding: '7px 10px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, fontFamily: 'inherit', background: 'var(--surface)' }}>
          <option value="">全部类型</option>
          {Object.entries(TYPE_NAMES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <button className="btn btn-primary btn-sm" onClick={handleUpload}>上传文档</button>
      </div>

      {message && (
        <div className="view-status loading" style={{ marginBottom: 12 }}>
          {message}
          <button className="btn btn-sm btn-secondary" style={{ marginLeft: 8 }} onClick={() => setMessage('')}>×</button>
        </div>
      )}

      <StatusCard loading={loading} error={error}>
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
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
