import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import { useMobileStore } from '../stores/mobileStore'

export default function DashboardLayout() {
  const sidebarOpen = useMobileStore((s) => s.sidebarOpen)
  const closeSidebar = useMobileStore((s) => s.closeSidebar)

  return (
    <>
      <Sidebar />
      <div
        className={`sidebar-overlay${sidebarOpen ? ' visible' : ''}`}
        onClick={closeSidebar}
      />
      <div className="main" id="main">
        <Header />
        <div className="content page-enter">
          <Outlet />
        </div>
      </div>
    </>
  )
}
