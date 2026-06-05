import { useEffect, useState } from 'react'
import type { DistributionTask, DistributionChannel, DistributionFile } from '../types'
import { mockTasks, mockChannels, mockFiles } from '../mock/distribution'
import StatusCard from '../components/StatusCard'
import Modal from '../components/Modal'
import TaskStatusBadge from '../components/TaskStatusBadge'
import TaskFormModal from '../components/TaskFormModal'
import { distributionApi } from '../api/distribution'

const PAGE_SIZE = 8
const STATUS_OPTIONS = [
  { value: '', label: '全部' },
  { value: 'active', label: '运行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'completed', label: '已完成' },
  { value: 'failed', label: '失败' },
  { value: 'draft', label: '草稿' },
]

export default function DistributionTasksPage() {
  const [tasks, setTasks] = useState<DistributionTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(0)
  const [deleteTarget, setDeleteTarget] = useState<DistributionTask | null>(null)
  const [message, setMessage] = useState('')

  // Form modal
  const [formOpen, setFormOpen] = useState(false)
  const [editingTask, setEditingTask] = useState<Partial<any> | null>(null)
  const [files, setFiles] = useState<DistributionFile[]>([])
  const [channels, setChannels] = useState<DistributionChannel[]>([])

  const fetchTasks = () => {
    setLoading(true)
    distributionApi.listTasks(1, 100, statusFilter || undefined)
      .then((r) => {
        setTasks(r.data.items ?? [])
        setError(null)
      })
      .catch((e) => {
        setError(e?.message || '获取任务列表失败')
        setTasks(mockTasks)
      })
      .finally(() => setLoading(false))
  }

  const fetchFilesAndChannels = () => {
    Promise.allSettled([
      distributionApi.listFiles(1, 100),
      distributionApi.listChannels(1, 100),
    ]).then(([fRes, cRes]) => {
      if (fRes.status === 'fulfilled') {
        setFiles(fRes.value.data.items ?? [])
      } else {
        setFiles(mockFiles)
      }
      if (cRes.status === 'fulfilled') {
        setChannels(cRes.value.data.items ?? [])
      } else {
        setChannels(mockChannels)
      }
    }).catch(() => {
      setFiles(mockFiles)
      setChannels(mockChannels)
    })
  }

  useEffect(() => { fetchTasks() }, [statusFilter])
  useEffect(() => { if (formOpen) fetchFilesAndChannels() }, [formOpen])

  const filtered = tasks.filter((t) => {
    if (statusFilter && t.status !== statusFilter) return false
    return true
  })
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const pageItems = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await distributionApi.deleteTask(deleteTarget.id)
      setTasks((prev) => prev.filter((t) => t.id !== deleteTarget.id))
      setMessage('任务已删除')
    } catch {
      setMessage('删除失败')
    }
    setDeleteTarget(null)
  }

  const handleTrigger = async (id: string) => {
    try {
      await distributionApi.triggerTask(id)
      setMessage('任务已触发，正在发送')
      fetchTasks()
    } catch {
      setMessage('触发失败')
    }
  }

  const handlePause = async (id: string) => {
    try {
      await distributionApi.pauseTask(id)
      setTasks((prev) => prev.map((t) => t.id === id ? { ...t, status: 'paused' } : t))
      setMessage('任务已暂停')
    } catch { setMessage('操作失败') }
  }

  const handleResume = async (id: string) => {
    try {
      await distributionApi.resumeTask(id)
      setTasks((prev) => prev.map((t) => t.id === id ? { ...t, status: 'active' } : t))
      setMessage('任务已恢复')
    } catch { setMessage('操作失败') }
  }

  const handleSave = async (data: any) => {
    try {
      await distributionApi.createTask(data)
      setFormOpen(false)
      setEditingTask(null)
      fetchTasks()
      setMessage('任务创建成功')
    } catch (e: any) {
      setMessage(e?.response?.data?.detail || '创建失败')
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>文件分发</h2>
        <button className="btn btn-primary" onClick={() => { setEditingTask(null); setFormOpen(true) }}>新建任务</button>
      </div>

      <div className="search-bar">
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`btn btn-sm ${statusFilter === opt.value ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => { setStatusFilter(opt.value); setPage(0) }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {message && (
        <div className="view-status loading" style={{ marginBottom: 12 }}>
          {message}
          <button className="btn btn-sm btn-secondary" style={{ marginLeft: 8 }} onClick={() => setMessage('')}>×</button>
        </div>
      )}

      <StatusCard loading={loading} error={error} empty={filtered.length === 0} emptyMessage="暂无分发任务，点击新建任务开始">
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>任务名称</th>
                  <th>文件</th>
                  <th>目标渠道</th>
                  <th>定时规则</th>
                  <th>下次执行</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((task) => (
                  <tr key={task.id}>
                    <td style={{ fontWeight: 500 }}>{task.name}</td>
                    <td style={{ fontSize: 12 }}>{task.file_name || '—'}</td>
                    <td style={{ fontSize: 12 }}>{task.channel_name || '—'}</td>
                    <td style={{ fontSize: 12 }}>
                      {{ once: '一次性', daily: '每天', weekly: '每周', monthly: '每月' }[task.schedule_type] || task.schedule_type}
                      {task.schedule_type !== 'once' && task.schedule_config?.hour != null && (
                        <span style={{ color: 'var(--color-text-muted)' }}> {String(task.schedule_config.hour).padStart(2, '0')}:{String(task.schedule_config.minute || 0).padStart(2, '0')}</span>
                      )}
                    </td>
                    <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                      {task.scheduled_at ? new Date(task.scheduled_at).toLocaleString('zh-CN') : '—'}
                    </td>
                    <td><TaskStatusBadge status={task.status} /></td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        <button className="btn btn-sm btn-secondary" onClick={() => handleTrigger(task.id)} title="立即执行">▶</button>
                        {task.status === 'active' && (
                          <button className="btn btn-sm btn-secondary" onClick={() => handlePause(task.id)} title="暂停">⏸</button>
                        )}
                        {task.status === 'paused' && (
                          <button className="btn btn-sm btn-secondary" onClick={() => handleResume(task.id)} title="恢复">▶</button>
                        )}
                        <button className="btn btn-sm btn-secondary" onClick={() => { setEditingTask(task); setFormOpen(true) }} title="编辑">✏</button>
                        <button className="btn btn-sm btn-secondary" onClick={() => setDeleteTarget(task)} title="删除" style={{ color: 'var(--color-danger)' }}>🗑</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {pageItems.length === 0 && (
                  <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 24 }}>暂无匹配的任务</td></tr>
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

      <TaskFormModal
        open={formOpen}
        initial={editingTask}
        files={files}
        channels={channels}
        onSave={handleSave}
        onCancel={() => { setFormOpen(false); setEditingTask(null) }}
      />

      <Modal
        open={!!deleteTarget}
        title="确认删除"
        message={`确定要删除任务 "${deleteTarget?.name || ''}" 吗？此操作不可撤销。`}
        confirmLabel="删除"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  )
}
