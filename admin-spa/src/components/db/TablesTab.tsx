import { useEffect, useState } from 'react'
import api from '../../api/client'

interface TableMeta {
  name: string
  writable_fields: string[] | null
  deletable: boolean
}

const PAGE_SIZE = 20

export default function TablesTab() {
  const [tables, setTables] = useState<TableMeta[]>([])
  const [selected, setSelected] = useState<string>('')
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ tables: TableMeta[] }>('/admin/db/tables')
      .then((r) => {
        setTables(r.data.tables)
        if (r.data.tables.length > 0) setSelected(r.data.tables[0].name)
      })
      .catch((e) => setError(e?.message || 'Failed to load tables'))
  }, [])

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    setError(null)
    api.get<{ data: Record<string, unknown>[]; total: number; page: number; page_size: number }>(
      `/admin/db/${selected}?page=${page}&page_size=${PAGE_SIZE}`
    )
      .then((r) => { setRows(r.data.data); setTotal(r.data.total) })
      .catch((e) => setError(e?.message || 'Failed to load rows'))
      .finally(() => setLoading(false))
  }, [selected, page])

  const columns = rows.length > 0 ? Object.keys(rows[0]) : []
  const selectedMeta = tables.find((t) => t.name === selected)
  const writeHint = selectedMeta
    ? selectedMeta.writable_fields === null
      ? '全字段可写'
      : (selectedMeta.writable_fields.length
          ? `仅可写: ${selectedMeta.writable_fields.join(', ')}`
          : '只读')
    : ''
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <label>选择表：</label>
        <select value={selected} onChange={(e) => { setSelected(e.target.value); setPage(1) }} style={{ padding: '4px 8px' }}>
          {tables.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
        </select>
        {selected && (
          <span style={{ marginLeft: 16, fontSize: 12, color: '#666' }}>
            {writeHint}{selectedMeta?.deletable ? ' · 可删除' : ''}
          </span>
        )}
      </div>
      {error && <div style={{ color: 'var(--color-danger, #dc2626)', padding: 8 }}>{error}</div>}
      {loading ? (
        <div>加载中...</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: 16, color: '#999' }}>无数据</div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c} style={{ textAlign: 'left', padding: '8px 12px', borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {columns.map((c) => (
                    <td key={c} style={{ padding: '6px 12px', borderBottom: '1px solid #f3f4f6', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {typeof r[c] === 'object' ? JSON.stringify(r[c]) : String(r[c] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
            <span>第 {page} 页 · 共 {totalPages} 页 ({total} 条)</span>
            <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</button>
          </div>
        </div>
      )}
    </div>
  )
}
