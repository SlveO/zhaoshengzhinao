import { useEffect, useState } from 'react'
import type { DistributionLog } from '../types'
import { mockLogs } from '../mock/distribution'
import StatusCard from '../components/StatusCard'
import TaskStatusBadge from '../components/TaskStatusBadge'
import { distributionApi } from '../api/distribution'

const PAGE_SIZE = 10

export default function DistributionLogsPage() {
  const [logs, setLogs] = useState<DistributionLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const fetchLogs = () => {
    setLoading(true)
    distributionApi.listLogs(1, 200, statusFilter ? { status: statusFilter } : undefined)
      .then((r) => {
        setLogs(r.data.items ?? [])
        setError(null)
      })
      .catch((e) => {
        setError(e?.message || '获取日志失败')
        setLogs(mockLogs)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchLogs() }, [statusFilter])

  const filtered = logs
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageItems = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const formatBytes = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>分发日志</h2>
      </div>

      <div className="search-bar">
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {[
            { value: '', label: '全部' },
            { value: 'success', label: '成功' },
            { value: 'failed', label: '失败' },
            { value: 'pending', label: '等待中' },
          ].map((opt) => (
            <button
              key={opt.value}
              className={`btn btn-sm ${statusFilter === opt.value ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => { setStatusFilter(opt.value); setPage(0) }}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <button className="btn btn-secondary btn-sm" onClick={fetchLogs}>刷新</button>
      </div>

      <StatusCard loading={loading} error={error} empty={filtered.length === 0} emptyMessage="暂无分发日志">
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>任务</th>
                  <th>渠道</th>
                  <th>文件</th>
                  <th>状态</th>
                  <th>尝试</th>
                  <th>耗时</th>
                  <th>错误</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((log) => (
                  <>
                    <tr
                      key={log.id}
                      onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                        {new Date(log.created_at).toLocaleString('zh-CN')}
                      </td>
                      <td style={{ fontSize: 12, fontWeight: 500 }}>{log.task_name || log.task_id}</td>
                      <td style={{ fontSize: 12 }}>{log.channel_name || log.channel_id}</td>
                      <td style={{ fontSize: 12 }}>{log.file_name || log.file_id}</td>
                      <td><TaskStatusBadge status={log.status} type="log" /></td>
                      <td style={{ fontSize: 12 }}>{log.attempt}</td>
                      <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                        {log.duration_ms != null ? `${log.duration_ms}ms` : '—'}
                      </td>
                      <td style={{ fontSize: 11, color: 'var(--color-danger)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.error_message || '—'}
                      </td>
                    </tr>
                    {expandedId === log.id && (
                      <tr key={`${log.id}-detail`}>
                        <td colSpan={8} style={{ background: '#f8fafc', padding: 16 }}>
                          <div style={{ fontSize: 12 }}>
                            {log.request_payload && (
                              <div style={{ marginBottom: 8 }}>
                                <strong style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>请求内容:</strong>
                                <pre style={{ margin: '4px 0 0', padding: 8, background: '#fff', borderRadius: 4, border: '1px solid var(--color-border)', overflow: 'auto', maxHeight: 200 }}>
                                  {JSON.stringify(log.request_payload, null, 2)}
                                </pre>
                              </div>
                            )}
                            {log.response_body && (
                              <div>
                                <strong style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>响应内容:</strong>
                                <pre style={{ margin: '4px 0 0', padding: 8, background: '#fff', borderRadius: 4, border: '1px solid var(--color-border)', overflow: 'auto', maxHeight: 200 }}>
                                  {JSON.stringify(log.response_body, null, 2)}
                                </pre>
                              </div>
                            )}
                            {!log.request_payload && !log.response_body && (
                              <span style={{ color: 'var(--color-text-muted)' }}>无详细信息</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
                {pageItems.length === 0 && (
                  <tr><td colSpan={8} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 24 }}>暂无日志</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        {totalPages > 1 && (
          <div className="pagination">
            <button className="btn btn-secondary btn-sm" onClick={() => setPage(0)} disabled={page === 0}>首页</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => p - 1)} disabled={page === 0}>上一页</button>
            <span>第 {page + 1} / {totalPages} 页（共 {filtered.length} 条）</span>
            <button className="btn btn-secondary btn-sm" onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages - 1}>下一页</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setPage(totalPages - 1)} disabled={page >= totalPages - 1}>末页</button>
          </div>
        )}
      </StatusCard>
    </div>
  )
}
