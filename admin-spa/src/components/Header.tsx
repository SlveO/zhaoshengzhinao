import { useEffect, useRef, useState } from 'react'
import { Menu, LogOut, ChevronDown, UserCircle } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useBrandConfig } from '../hooks/useBrandConfig'
import { useMobileStore } from '../stores/mobileStore'

export default function Header() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const { brand } = useBrandConfig()
  const [time, setTime] = useState('')
  const isMobile = useMobileStore((s) => s.isMobile)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function update() {
      const d = new Date()
      setTime(
        isMobile
          ? d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'numeric', day: 'numeric' })
          : d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' }),
      )
    }
    update()
    const id = setInterval(update, 60000)
    return () => clearInterval(id)
  }, [isMobile])

  // 点击外部关闭下拉
  useEffect(() => {
    if (!menuOpen) return
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [menuOpen])

  const toggleSidebar = useMobileStore((s) => s.toggleSidebar)

  const collegeName = brand?.name || '招生院校'
  const roleLabel = user?.is_developer ? '开发者账号' : '院校管理员'

  return (
    <header className="header">
      <button className="hamburger" onClick={toggleSidebar} aria-label="菜单">
        <Menu size={22} />
      </button>
      <div className="header-brand">
        {brand?.logo_url ? (
          <img className="logo-img" src={brand.logo_url} alt="" />
        ) : (
          <div className="logo-fallback">{brand?.name ? brand.name[0] : '华'}</div>
        )}
        <div className="sep" />
        <span className="title">招生管理平台</span>
      </div>

      <div className="header-right">
        <span className="header-date">{time}</span>

        {/* 账号下拉菜单（替代无响应的按钮 + 已删除的假消息铃铛） */}
        <div ref={menuRef} style={{ position: 'relative' }}>
          <button
            className="header-user"
            onClick={() => setMenuOpen((v) => !v)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            style={{
              background: menuOpen ? 'var(--color-bg-elevated, #f3f4f6)' : 'transparent',
            }}
          >
            <div className="avatar">{user?.username?.[0] || '管'}</div>
            {isMobile ? (
              <span className="uname" style={{ maxWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user?.username || '管理员'}
              </span>
            ) : (
              <span className="uname">{user?.username || '管理员'}</span>
            )}
            <ChevronDown size={14} style={{ transition: 'transform 0.2s', transform: menuOpen ? 'rotate(180deg)' : 'none' }} />
          </button>

          {menuOpen && (
            <div
              role="menu"
              style={{
                position: 'absolute',
                right: 0,
                top: 'calc(100% + 6px)',
                minWidth: 220,
                background: '#fff',
                border: '1px solid var(--color-border, #e5e7eb)',
                borderRadius: 8,
                boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
                padding: 8,
                zIndex: 1000,
              }}
            >
              <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--color-border, #e5e7eb)', marginBottom: 6 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                  <UserCircle size={18} style={{ color: 'var(--color-text-muted, #6b7280)' }} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary, #1f2937)' }}>
                      {user?.username || '管理员'}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--color-text-muted, #6b7280)' }}>
                      {roleLabel}
                    </div>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #4b5563)', lineHeight: 1.5 }}>
                  <div>所属院校：</div>
                  <div style={{ fontWeight: 500, color: 'var(--color-text-primary, #1f2937)' }}>{collegeName}</div>
                </div>
              </div>
              <button
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  logout()
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  width: '100%',
                  padding: '8px 12px',
                  background: 'transparent',
                  border: 'none',
                  borderRadius: 6,
                  cursor: 'pointer',
                  fontSize: 13,
                  color: 'var(--color-danger, #dc2626)',
                }}
              >
                <LogOut size={16} />
                退出登录
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
