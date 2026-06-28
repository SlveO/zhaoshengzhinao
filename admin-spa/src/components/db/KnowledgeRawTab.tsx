import { useEffect, useRef, useState } from 'react'
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

interface ReindexProgress {
  status: 'idle' | 'running' | 'completed' | 'failed'
  total: number
  done: number
  started_at: string | null
  finished_at: string | null
  error: string | null
  triggered_by: string
  percent: number
}

interface IndexStatus {
  total_docs: number
  indexed_docs: number
  pending_docs: number
  reindex: ReindexProgress
}

const POLL_INTERVAL = 1500 // ms

export default function KnowledgeRawTab() {
  const [docs, setDocs] = useState<RawDoc[]>([])
  const [selected, setSelected] = useState<RawDoc | null>(null)
  const [draft, setDraft] = useState<string>('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [search, setSearch] = useState('')
  const [reindexProgress, setReindexProgress] = useState<ReindexProgress | null>(null)
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchDocs = () => {
    api.get<{ documents: RawDoc[] }>('/admin/db/knowledge/raw')
      .then((r) => setDocs(r.data.documents))
      .catch((e) => setError(e?.message || '加载失败'))
  }

  // 轮询索引进度
  const pollIndexStatus = () => {
    api.get<IndexStatus>('/admin/knowledge/index-status')
      .then((r) => {
        setReindexProgress(r.data.reindex)
        // 仍在运行 → 继续轮询
        if (r.data.reindex.status === 'running') {
          pollTimer.current = setTimeout(pollIndexStatus, POLL_INTERVAL)
        } else {
          // 完成/失败 → 刷新文档列表以更新 indexed_at 标记
          if (r.data.reindex.status === 'completed' || r.data.reindex.status === 'failed') {
            fetchDocs()
          }
        }
      })
      .catch(() => {
        // 轮询失败 → 重试一次
        pollTimer.current = setTimeout(pollIndexStatus, POLL_INTERVAL * 2)
      })
  }

  const startPolling = () => {
    if (pollTimer.current) clearTimeout(pollTimer.current)
    pollIndexStatus()
  }

  useEffect(() => {
    fetchDocs()
    // 启动时检查是否有正在进行的索引
    api.get<IndexStatus>('/admin/knowledge/index-status')
      .then((r) => {
        if (r.data.reindex.status === 'running') {
          setReindexProgress(r.data.reindex)
          startPolling()
        }
      })
      .catch(() => {})

    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current)
    }
  }, [])

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
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(draft)
    } catch (e) {
      setError('JSON 解析失败: ' + (e instanceof Error ? e.message : ''))
      setSaving(false)
      return
    }
    try {
      const r = await api.put<{
        reindex_started: boolean
        reindex_status: string
      }>(`/admin/db/knowledge/raw/${selected.id}`, { content: parsed })
      if (r.data.reindex_started) {
        setMessage('已保存，正在后台重新索引…')
        startPolling()
      } else {
        setMessage('已保存（已有索引任务在跑，本次编辑将在该任务完成后生效）')
      }
      fetchDocs()
    } catch (e) {
      setError('保存失败: ' + (e instanceof Error ? e.message : ''))
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

  const isIndexing = reindexProgress?.status === 'running'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 220px)', minHeight: 480 }}>
      {/* 顶部全局索引进度条（无论是否选中文档都显示） */}
      {reindexProgress && reindexProgress.status !== 'idle' && (
        <div style={{ marginBottom: 8 }}>
          <ReindexProgressBar progress={reindexProgress} />
        </div>
      )}
    <div
      style={{
        display: 'flex',
        gap: 16,
        flex: 1,
        minHeight: 0,
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
              <button
                onClick={onSave}
                disabled={saving}
                style={{
                  padding: '6px 16px',
                  background: 'var(--color-primary, #1a3a6b)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 4,
                  cursor: saving ? 'not-allowed' : 'pointer',
                  opacity: saving ? 0.6 : 1,
                }}
              >
                {saving ? '保存中...' : '保存并重新索引'}
              </button>
            </div>

            {/* 错误/成功提示 */}
            {error && <div style={{ color: 'var(--color-danger, #dc2626)', marginBottom: 8, fontSize: 13 }}>{error}</div>}
            {message && !isIndexing && <div style={{ color: 'var(--color-success, #16a34a)', marginBottom: 8, fontSize: 13 }}>{message}</div>}

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
    </div>
  )
}

function ReindexProgressBar({ progress }: { progress: ReindexProgress }) {
  const { status, total, done, percent, error, triggered_by } = progress

  const bg =
    status === 'running' ? '#eff6ff'
    : status === 'completed' ? '#f0fdf4'
    : status === 'failed' ? '#fef2f2'
    : '#f9fafb'

  const color =
    status === 'running' ? '#2563eb'
    : status === 'completed' ? '#16a34a'
    : status === 'failed' ? '#dc2626'
    : '#666'

  const label =
    status === 'running' ? `正在重建索引 (${done}/${total})`
    : status === 'completed' ? `索引完成 (${total} 条)`
    : status === 'failed' ? `索引失败: ${error || '未知错误'}`
    : ''

  return (
    <div
      style={{
        marginBottom: 8,
        padding: '8px 12px',
        background: bg,
        border: `1px solid ${color}33`,
        borderRadius: 4,
        fontSize: 12,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <span style={{ color, fontWeight: 500 }}>
          {status === 'running' && '⚙ '}
          {status === 'completed' && '✓ '}
          {status === 'failed' && '✗ '}
          {label}
        </span>
        <span style={{ color: '#666', fontSize: 11 }}>
          {triggered_by === 'raw_edit' ? '由编辑触发' : triggered_by === 'startup' ? '启动时触发' : '手动触发'}
        </span>
      </div>
      {status === 'running' && (
        <div style={{ background: '#e5e7eb', borderRadius: 2, height: 6, overflow: 'hidden' }}>
          <div
            style={{
              width: `${percent}%`,
              height: '100%',
              background: color,
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      )}
    </div>
  )
}
