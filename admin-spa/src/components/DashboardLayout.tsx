import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function DashboardLayout() {
  return (
    <>
      <Sidebar />
      <div className="main" id="main">
        <Header />
        <div className="content page-enter">
          <Outlet />
        </div>
      </div>
    </>
  )
}
