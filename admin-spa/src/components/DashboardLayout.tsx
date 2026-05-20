import { Outlet, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Sidebar from './Sidebar'

const VIEW_TITLES: Record<string, string> = {
  '/dashboard': '数据仪表盘',
  '/profile': '画像看板',
  '/insights': '增强分析',
  '/knowledge': '知识库管理',
  '/brand': '品牌设置',
  '/agent-settings': 'AI 对话设置',
  '/modules': '模块管理',
  '/reports': '招生优化报告',
}

export default function DashboardLayout() {
  const location = useLocation()
  const [time, setTime] = useState('')
  const title = VIEW_TITLES[location.pathname] || '管理后台'

  useEffect(() => {
    function update() {
      const now = new Date()
      setTime(
        now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' }) +
        ' ' + now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
      )
    }
    update()
    const id = setInterval(update, 30000)
    return () => clearInterval(id)
  }, [])

  return (
    <>
      <Sidebar />
      <div className="main">
        <div className="topbar">
          <span className="view-title">{title}</span>
          <span className="topbar-meta">{time}</span>
        </div>
        <div className="content">
          <Outlet />
        </div>
      </div>
    </>
  )
}
