const STATUS_MAP: Record<string, { label: string; className: string }> = {
  draft: { label: '草稿', className: 'pill' },
  active: { label: '运行中', className: 'pill green' },
  paused: { label: '已暂停', className: 'pill amber' },
  completed: { label: '已完成', className: 'pill green' },
  failed: { label: '失败', className: 'pill red' },
  pending: { label: '等待中', className: 'pill' },
  sending: { label: '发送中', className: 'pill amber' },
  success: { label: '成功', className: 'pill green' },
}

export default function TaskStatusBadge({ status, type = 'task' }: { status: string; type?: 'task' | 'log' }) {
  const key = type === 'log' && status === 'success' ? 'success' :
              type === 'log' && status === 'failed' ? 'failed' :
              type === 'log' && status === 'sending' ? 'sending' :
              status

  const config = STATUS_MAP[key] || { label: status, className: 'pill' }

  return <span className={config.className}>{config.label}</span>
}
