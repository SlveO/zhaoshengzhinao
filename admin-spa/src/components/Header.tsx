import { useEffect, useState } from 'react'
import { Bell } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useBrandConfig } from '../hooks/useBrandConfig'

export default function Header() {
  const user = useAuthStore((s) => s.user)
  const { brand } = useBrandConfig()
  const [time, setTime] = useState('')
  const unread = 3 // TODO: replace with API unreadNotificationCount

  useEffect(() => {
    function update() {
      const d = new Date()
      setTime(
        d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' }),
      )
    }
    update()
    const id = setInterval(update, 60000)
    return () => clearInterval(id)
  }, [])

  return (
    <header className="header">
      <div className="header-brand">
        {brand?.logo_url ? (
          <img className="logo-img" src={brand.logo_url} alt="" />
        ) : (
          <div className="logo-fallback">{(brand?.name || '招')[0]}</div>
        )}
        <div className="sep" />
        <span className="title">招生管理平台</span>
      </div>

      <div className="header-right">
        <span className="header-date">{time}</span>

        <button className="header-notify">
          <Bell size={18} />
          {unread > 0 && <span className="badge">{unread > 99 ? '99+' : unread}</span>}
        </button>

        <button className="header-user">
          <div className="avatar">{user?.username?.[0] || '管'}</div>
          <span className="uname">{user?.username || '管理员'}</span>
          <svg className="chevron" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m6 9 6 6 6-6"/></svg>
        </button>
      </div>
    </header>
  )
}
