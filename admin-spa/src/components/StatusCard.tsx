import type { ReactNode } from 'react'

interface StatusCardProps {
  loading?: boolean
  error?: string | null
  empty?: boolean
  emptyIcon?: string
  emptyMessage?: string
  emptyHint?: string
  children?: ReactNode
}

export default function StatusCard({
  loading,
  error,
  empty,
  emptyIcon,
  emptyMessage = '暂无数据',
  emptyHint,
  children,
}: StatusCardProps) {
  if (loading) {
    return (
      <div className="status-card flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[var(--brand-primary)] border-t-transparent rounded-full animate-spin" />
          <span className="text-sm text-gray-400">加载中...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="status-card flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3 max-w-xs text-center">
          <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          </div>
          <p className="text-sm text-red-500">{error}</p>
        </div>
      </div>
    )
  }

  if (empty) {
    return (
      <div className="status-card flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3 max-w-xs text-center">
          {emptyIcon && <span className="text-4xl opacity-60">{emptyIcon}</span>}
          <p className="text-sm font-medium text-gray-500">{emptyMessage}</p>
          {emptyHint && <p className="text-xs text-gray-400 leading-relaxed">{emptyHint}</p>}
        </div>
      </div>
    )
  }

  return <>{children}</>
}
