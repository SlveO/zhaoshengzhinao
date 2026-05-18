import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAuthStore } from '../stores/authStore'

export default function DashboardLayout() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />

      <div
        className="flex-1 flex flex-col transition-all"
        style={{ marginLeft: 'var(--sidebar-width)' }}
      >
        <header
          className="flex items-center justify-end gap-4 px-6 border-b bg-white flex-shrink-0"
          style={{ height: 'var(--header-height)' }}
        >
          <span className="text-sm text-gray-500">{user?.username}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-400 hover:text-red-500 transition-colors cursor-pointer"
          >
            退出登录
          </button>
        </header>

        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
