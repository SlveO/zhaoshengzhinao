import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import api from '../api/client'
import type { TenantConfig } from '../types'
import { useAuthStore } from '../stores/authStore'

const ALL_MENU_ITEMS = [
  { path: '/dashboard', label: '数据仪表盘', module: null, icon: '◫', section: '总览' },
  { path: '/profile', label: '画像看板', module: 'profile_dashboard', icon: '◉', section: '招生分析' },
  { path: '/insights', label: '增强分析', module: 'topic_cloud', icon: '◎', section: '招生分析' },
  { path: '/knowledge', label: '知识库管理', module: null, icon: '▦', section: '配置管理' },
  { path: '/brand', label: '品牌设置', module: null, icon: '◧', section: '配置管理' },
  { path: '/agent-settings', label: 'AI 对话设置', module: null, icon: '◈', section: '配置管理' },
  { path: '/modules', label: '模块管理', module: null, icon: '⊞', section: '配置管理' },
  { path: '/reports', label: '招生优化报告', module: 'funnel', icon: '☰', section: '决策支持' },
]

export default function Sidebar() {
  const [config, setConfig] = useState<TenantConfig | null>(null)
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    api.get<TenantConfig>('/admin/tenants/me/config').then((r) => setConfig(r.data))
  }, [])

  const visibleItems = ALL_MENU_ITEMS.filter((item) => {
    if (!item.module) return true
    return config?.modules?.[item.module] ?? false
  })

  const brand = config?.brand
  const brandName = brand?.short_name || brand?.name || '招生智脑'

  let lastSection = ''

  return (
    <aside className="sidebar" id="sidebar">
      <div className="sidebar-brand">
        <div className="logo">{brandName[0]}</div>
        <div className="name">
          {brand?.name || '招生智脑'}
          <small>院校管理后台</small>
        </div>
      </div>
      <nav className="sidebar-nav">
        {visibleItems.map((item) => {
          const showSection = item.section !== lastSection
          lastSection = item.section
          return (
            <div key={item.path}>
              {showSection && <div className="nav-section">{item.section}</div>}
              <NavLink
                to={item.path}
                className={({ isActive }) => `nav-btn${isActive ? ' active' : ''}`}
              >
                <span className="icon">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </div>
          )
        })}
      </nav>
      <div className="sidebar-footer">
        <div className="avatar">{user?.username?.[0] || '管'}</div>
        <div className="user-info">
          <div className="uname">{user?.username || '管理员'}</div>
          <div className="urole">{brandName} 招生办</div>
        </div>
        <button className="logout-btn" onClick={logout} title="退出登录">⏻</button>
      </div>
    </aside>
  )
}
