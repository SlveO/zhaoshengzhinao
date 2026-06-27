import { useEffect, useState } from 'react'
import api from '../../api/client'
import MonacoEditor from '@monaco-editor/react'

interface RawDoc {
  id: string
  title: string
  data_type: string
  year: number | null
  content: Record<string, any>
  indexed_at: string | null
}

export default function KnowledgeRawTab() {
  const [docs, setDocs] = useState<RawDoc[]>([])
  const [selected, setSelected] = useState<RawDoc | null>(null)
  const [draft, setDraft] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [search, setSearch] = useState('')

  const fetchDocs = () => {
    api.get<{ documents: RawDoc[] }>('/admin/db/knowledge/raw')
      .then((r) => setDocs(r.data.documents))
      .catch((e) => setError(e?.message || '加载失败'))
  }

  useEffect(() => { fetchDocs() }, [])

  const onSelect = (d: RawDoc) => {
    setSelected(d)
    setDraft(JSON.stringify(d.content, null, 2))
    setMessage('')
    setError(null)
  }

  const onSave = async () => {
    if (!selected) return
    setSaving(true)
    setMessage('')
    setError(null)
    let parsed: Record<string, any>
    try {
      parsed = JSON.parse(draft)
    } catch (e: any) {
      setError('JSON 解析失败: ' + e.message)
      setSaving(false)
      return
    }
    try {
      await api.put(`/admin/db/knowledge/raw/${selected.id}`, { content: parsed })
      setMessage('已保存，ChromaDB 已重新索引')
      fetchDocs()
    } catch (e: any) {
      setError('保存失败: ' + (e?.message || ''))
    } finally {
      setSaving(false)
    }
  }

  const filteredDocs = docs.filter((d) => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return (
      d.title.toLowerCase().includes(q) ||
      d.data_type.toLowerCase().includes(q) ||
      String(d.year || '').includes(q)
    )
  })

  return (
    <div
      style={{
        display: 'flex',
        gap: 16,
        height: 'calc(100vh - 220px)',
        minHeight: 480,
        alignItems: 'stretch',
      }}
    >
      {/* 左侧：文档列表 + 搜索（独立滚动） */}
      <div
        style={{
          width: 280,
          flexShrink: 0,
          borderRight: '1px solid #e5e7eb',
          paddingRight: 12,
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
        }}
      >
        <h3 style={{ fontSize: 14, marginBottom: 8 }}>
          知识库文档 ({docs.length}{search ? ` / 筛选 ${filteredDocs.length}` : ''})
        </h3>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索标题 / 类型 / 年份…"
          style={{
            padding: '6px 10px',
            marginBottom: 8,
            border: '1px solid #e5e7eb',
            borderRadius: 4,
            fontSize: 12,
            outline: 'none',
          }}
        />
        <div style={{ overflowY: 'auto', flex: 1, minHeight: 0, paddingRight: 4 }}>
          {filteredDocs.length === 0 ? (
            <div style={{ padding: 16, fontSize: 12, color: '#999', textAlign: 'center' }}>
              {search ? '无匹配文档' : '加载中...'}
            </div>
          ) : (
            filteredDocs.map((d) => (
              <div
                key={d.id}
                onClick={() => onSelect(d)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  background: selected?.id === d.id ? '#eff6ff' : 'transparent',
                  borderLeft: selected?.id === d.id ? '3px solid #2563eb' : '3px solid transparent',
                  borderRadius: 4,
                  marginBottom: 4,
                  fontSize: 13,
                }}
              >
                <div style={{ fontWeight: 500 }}>{d.title}</div>
                <div style={{ fontSize: 11, color: '#666' }}>
                  {d.data_type} · {d.year || '-'} · {d.indexed_at ? '已索引' : '未索引'}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* 右侧：编辑器（独立滚动） */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {!selected ? (
          <div style={{ padding: 32, color: '#999' }}>选择左侧文档查看/编辑 JSON</div>
        ) : (
          <>
            <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: 14 }}>{selected.title}</h3>
              <button onClick={onSave} disabled={saving} style={{ padding: '6px 16px', background: 'var(--color-primary, #1a3a6b)', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                {saving ? '保存中...' : '保存并重新索引'}
              </button>
            </div>
            {error && <div style={{ color: 'var(--color-danger, #dc2626)', marginBottom: 8 }}>{error}</div>}
            {message && <div style={{ color: 'var(--color-success, #16a34a)', marginBottom: 8 }}>{message}</div>}
            <div style={{ border: '1px solid #e5e7eb', flex: 1, minHeight: 0 }}>
              <MonacoEditor
                height="100%"
                language="json"
                value={draft}
                onChange={(v) => setDraft(v || '')}
                options={{ minimap: { enabled: false }, fontSize: 13 }}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
