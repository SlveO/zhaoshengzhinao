import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from '../api/client'
import type { TenantConfig } from '../types'

const ALL_MENU_ITEMS = [
  { path: '/funnel', label: '招生漏斗', module: 'funnel', icon: '📊' },
  { path: '/profile', label: '画像看板', module: 'profile_dashboard', icon: '👤' },
  { path: '/brand', label: '品牌设置', module: null, icon: '🎨' },
  { path: '/knowledge', label: '知识库', module: null, icon: '📚' },
  { path: '/insights', label: '增强分析', module: 'topic_cloud', icon: '📈' },
  { path: '/agent-settings', label: 'AI 设置', module: null, icon: '🤖' },
]

export default function Sidebar() {
  const [config, setConfig] = useState<TenantConfig | null>(null)

  useEffect(() => {
    api.get<TenantConfig>('/admin/tenants/me/config').then((r) => setConfig(r.data))
  }, [])

  const visibleItems = ALL_MENU_ITEMS.filter((item) => {
    if (!item.module) return true
    return config?.modules?.[item.module] ?? false
  })

  return (
    <aside
      className="flex flex-col fixed left-0 top-0 h-screen overflow-y-auto sidebar-scroll"
      style={{ width: 'var(--sidebar-width)', background: 'var(--sidebar-bg)' }}
    >
      <div className="flex items-center gap-3 px-5 py-4 border-b border-white/10">
        <div
          className="w-9 h-9 rounded-lg bg-white/15 flex-shrink-0 bg-center bg-contain bg-no-repeat"
          style={{ backgroundImage: 'var(--brand-logo)' }}
        />
        <span className="text-white font-semibold text-base truncate">
          {config?.brand?.short_name || config?.brand?.name || '管理后台'}
        </span>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-1">
        {visibleItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-white/20 text-white font-medium'
                  : 'text-white/70 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <span className="text-lg">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-3 border-t border-white/10">
        <span className="text-white/50 text-xs">
          {config?.brand?.name || ''}
        </span>
      </div>
    </aside>
  )
}
