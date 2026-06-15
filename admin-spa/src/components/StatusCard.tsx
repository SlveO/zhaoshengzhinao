import type { ReactNode } from 'react'

interface StatusCardProps {
  loading?: boolean
  error?: string | null
  empty?: boolean
  emptyMessage?: string
  children?: ReactNode
  onRetry?: () => void
}

export default function StatusCard({ loading, error, empty, emptyMessage = '暂无数据', children, onRetry }: StatusCardProps) {
  if (loading) {
    return (
      <div className="view-status loading">
        <div className="spinner" />
        <span>加载中...</span>
      </div>
    )
  }

  if (error && !children) {
    return (
      <div className="view-status error">
        <span>{error}</span>
        {onRetry && (
          <button className="btn btn-secondary btn-sm" onClick={onRetry}>重试</button>
        )}
      </div>
    )
  }

  if (empty && !children) {
    return (
      <div className="view-status empty">
        <span style={{ fontSize: 32, opacity: 0.4, marginBottom: 8 }}>📭</span>
        <span>{emptyMessage}</span>
      </div>
    )
  }

  return (
    <>
      {error && (
        <div
          style={{
            background: 'var(--color-warning-surface, #fef3c7)',
            color: 'var(--color-warning-text, #92400e)',
            padding: '8px 14px',
            borderRadius: 8,
            fontSize: 12,
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ opacity: 0.7, fontWeight: 500 }}>⚠ Demo 模式</span>
          <span style={{ opacity: 0.7 }}>—</span>
          <span style={{ opacity: 0.85 }}>API 不可用，当前显示模拟数据</span>
        </div>
      )}
      {children}
    </>
  )
}
