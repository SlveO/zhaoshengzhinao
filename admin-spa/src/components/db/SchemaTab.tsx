import { useEffect, useState } from 'react'
import api from '../../api/client'

interface Column {
  name: string
  type: string
  nullable: boolean
  default: string | null
}

const th: React.CSSProperties = { textAlign: 'left', padding: '8px 12px', borderBottom: '2px solid #e5e7eb', background: '#f9fafb' }
const td: React.CSSProperties = { padding: '6px 12px', borderBottom: '1px solid #f3f4f6' }

export default function SchemaTab() {
  const [tables, setTables] = useState<string[]>([])
  const [selected, setSelected] = useState('')
  const [columns, setColumns] = useState<Column[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ tables: { name: string }[] }>('/admin/db/tables')
      .then((r) => {
        setTables(r.data.tables.map((t) => t.name))
        if (r.data.tables.length > 0) setSelected(r.data.tables[0].name)
      })
      .catch((e) => setError(e?.message || '加载失败'))
  }, [])

  useEffect(() => {
    if (!selected) return
    api.get<{ columns: Column[] }>(`/admin/db/${selected}/schema`)
      .then((r) => setColumns(r.data.columns))
      .catch((e) => setError(e?.message || '加载失败'))
  }, [selected])

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <label>选择表：</label>
        <select value={selected} onChange={(e) => setSelected(e.target.value)} style={{ padding: '4px 8px' }}>
          {tables.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      {error && <div style={{ color: 'var(--color-danger, #dc2626)' }}>{error}</div>}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={th}>字段名</th>
            <th style={th}>类型</th>
            <th style={th}>可空</th>
            <th style={th}>默认值</th>
          </tr>
        </thead>
        <tbody>
          {columns.map((c) => (
            <tr key={c.name}>
              <td style={td}><code>{c.name}</code></td>
              <td style={td}>{c.type}</td>
              <td style={td}>{c.nullable ? 'YES' : 'NO'}</td>
              <td style={td}>{c.default || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
