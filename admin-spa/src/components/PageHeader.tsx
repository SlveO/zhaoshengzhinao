import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  extra?: ReactNode
}

export default function PageHeader({ title, subtitle, extra }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="text-xl font-bold text-gray-800 tracking-tight">{title}</h2>
        {subtitle && (
          <p className="text-sm text-gray-400 mt-1 leading-relaxed">{subtitle}</p>
        )}
      </div>
      {extra && <div className="flex-shrink-0">{extra}</div>}
    </div>
  )
}
