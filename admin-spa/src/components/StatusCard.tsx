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

  if (error) {
    return (
      <div className="view-status error">
        <span>{error}</span>
        {onRetry && (
          <button className="btn btn-secondary btn-sm" onClick={onRetry}>重试</button>
        )}
      </div>
    )
  }

  if (empty) {
    return (
      <div className="view-status empty">
        <span style={{ fontSize: 32, opacity: 0.4, marginBottom: 8 }}>📭</span>
        <span>{emptyMessage}</span>
      </div>
    )
  }

  return <>{children}</>
}
