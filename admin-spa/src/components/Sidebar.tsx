import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  LayoutDashboard, MessageSquare, BarChart3,
  BookOpen, Bot, LogOut,
  Database,
} from 'lucide-react'
import api from '../api/client'
import type { TenantConfig } from '../types'
import { useAuthStore } from '../stores/authStore'
import { useMobileStore } from '../stores/mobileStore'

interface MenuItem {
  path: string
  label: string
  icon: React.ReactNode
  module: string | null
  section: string
}

const MENU_ITEMS: MenuItem[] = [
  { path: '/dashboard', label: '工作台', icon: <LayoutDashboard size={18} />, module: null, section: '导航' },
  { path: '/consultations', label: '咨询管理', icon: <MessageSquare size={18} />, module: null, section: '导航' },
  // 画像看板功能暂时隐藏(即将上线,功能待完善)
  // { path: '/profile', label: '画像看板', icon: <User size={18} />, module: 'profile_dashboard', section: '导航' },
  { path: '/insights', label: '洞察分析', icon: <BarChart3 size={18} />, module: 'topic_cloud', section: '导航' },
  { path: '/knowledge', label: '知识库', icon: <BookOpen size={18} />, module: null, section: '管理' },
  { path: '/agent-settings', label: 'Agent 设置', icon: <Bot size={18} />, module: null, section: '管理' },
]

export default function Sidebar() {
  const [config, setConfig] = useState<TenantConfig | null>(null)
  const logout = useAuthStore((s) => s.logout)
  const isDeveloper = useAuthStore((s) => s.user?.is_developer ?? false)
  const sidebarOpen = useMobileStore((s) => s.sidebarOpen)
  const isMobile = useMobileStore((s) => s.isMobile)
  const collapsed = useMobileStore((s) => s.collapsed)
  const closeSidebar = useMobileStore((s) => s.closeSidebar)

  useEffect(() => {
    api.get<TenantConfig>('/admin/tenants/me/config').then((r) => setConfig(r.data)).catch(() => {})
  }, [])

  // 同步 main 区域的 expanded class（桌面端收起时主区域扩展）
  useEffect(() => {
    const main = document.getElementById('main')
    if (!main) return
    if (collapsed && !isMobile) {
      main.classList.add('expanded')
    } else {
      main.classList.remove('expanded')
    }
  }, [collapsed, isMobile])

  const visibleItems = MENU_ITEMS.filter((item) => {
    if (!item.module) return true
    return config?.modules?.[item.module] ?? true
  })

  const brand = config?.brand
  const brandName = brand?.short_name || brand?.name || '招生智脑'

  return (
    <aside className={`sidebar${collapsed && !isMobile ? ' collapsed' : ''}${sidebarOpen ? ' open' : ''}`}>
      <div className="sidebar-brand">
        <div className="logo">{brandName[0]}</div>
        <div className="name">
          {brand?.name || '招生智脑'}
          <small>招生管理平台</small>
        </div>
      </div>

      <nav className="sidebar-nav" onClick={() => isMobile && closeSidebar()}>
        {visibleItems.map((item, idx) => {
          const showSection = idx === 0 || visibleItems[idx - 1].section !== item.section
          return (
            <div key={item.path}>
              {showSection && <div className="nav-section">{item.section}</div>}
              <NavLink
                to={item.path}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </div>
          )
        })}
        {isDeveloper && (
          <div>
            <div className="nav-section">开发者</div>
            <NavLink
              to="/db"
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
            >
              <span className="nav-icon"><Database size={18} /></span>
              <span>数据库管理</span>
            </NavLink>
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        <button
          className="collapse-btn"
          onClick={logout}
          title="退出登录"
          aria-label="退出登录"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: 'transparent',
            color: 'var(--color-text-muted, #6b7280)',
            border: '1px solid var(--color-border, #e5e7eb)',
            cursor: 'pointer',
          }}
        >
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  )
}
