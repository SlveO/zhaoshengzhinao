import { NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  LayoutDashboard, Users, MessageSquare, User, BarChart3, FileText, Radio,
  BookOpen, Palette, Bot, Blocks, ChevronLeft, ChevronRight, LogOut, Send,
} from 'lucide-react'
import api from '../api/client'
import type { TenantConfig } from '../types'
import { useAuthStore } from '../stores/authStore'

interface MenuItem {
  path: string
  label: string
  icon: React.ReactNode
  module: string | null
  section: string
}

const MENU_ITEMS: MenuItem[] = [
  { path: '/dashboard', label: '工作台', icon: <LayoutDashboard size={18} />, module: null, section: '导航' },
  { path: '/leads', label: '线索管理', icon: <Users size={18} />, module: null, section: '导航' },
  { path: '/consultations', label: '咨询管理', icon: <MessageSquare size={18} />, module: null, section: '导航' },
  { path: '/profile', label: '画像看板', icon: <User size={18} />, module: 'profile_dashboard', section: '导航' },
  { path: '/insights', label: '洞察分析', icon: <BarChart3 size={18} />, module: 'topic_cloud', section: '导航' },
  { path: '/reports', label: '招生报告', icon: <FileText size={18} />, module: null, section: '导航' },
  { path: '/channels', label: '渠道管理', icon: <Radio size={18} />, module: null, section: '导航' },
  { path: '/knowledge', label: '知识库', icon: <BookOpen size={18} />, module: null, section: '管理' },
  { path: '/brand', label: '品牌配置', icon: <Palette size={18} />, module: null, section: '管理' },
  { path: '/agent-settings', label: 'Agent 设置', icon: <Bot size={18} />, module: null, section: '管理' },
  { path: '/modules', label: '模块管理', icon: <Blocks size={18} />, module: null, section: '管理' },
  { path: '/distribution/tasks', label: '文件分发', icon: <Send size={18} />, module: 'distribution', section: '分发' },
  { path: '/distribution/channels', label: '分发渠道', icon: <Radio size={18} />, module: 'distribution', section: '分发' },
  { path: '/distribution/logs', label: '分发日志', icon: <FileText size={18} />, module: 'distribution', section: '分发' },
]

export default function Sidebar() {
  const [config, setConfig] = useState<TenantConfig | null>(null)
  const [collapsed, setCollapsed] = useState(false)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    api.get<TenantConfig>('/admin/tenants/me/config').then((r) => setConfig(r.data)).catch(() => {})
  }, [])

  const visibleItems = MENU_ITEMS.filter((item) => {
    if (!item.module) return true
    return config?.modules?.[item.module] ?? true
  })

  const brand = config?.brand
  const brandName = brand?.short_name || brand?.name || '招生智脑'

  let lastSection = ''

  return (
    <aside className={`sidebar${collapsed ? ' collapsed' : ''}`}>
      <div className="sidebar-brand">
        <div className="logo">{brandName[0]}</div>
        <div className="name">
          {brand?.name || '招生智脑'}
          <small>招生管理平台</small>
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
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            </div>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <button className="collapse-btn" onClick={() => {
          setCollapsed((v) => !v)
          document.getElementById('main')?.classList.toggle('expanded')
        }} title={collapsed ? '展开' : '收起'}>
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
        <div style={{ flex: 1 }} />
        <button className="collapse-btn" onClick={logout} title="退出登录">
          <LogOut size={16} />
        </button>
      </div>
    </aside>
  )
}
