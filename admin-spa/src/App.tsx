import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useBrandConfig } from './hooks/useBrandConfig'
import { useMobileStore } from './stores/mobileStore'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardLayout from './components/DashboardLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ConsultationsPage from './pages/ConsultationsPage'
// 画像看板功能暂时隐藏(即将上线,功能待完善)
// import ProfileDashboardPage from './pages/ProfileDashboardPage'
import InsightsPage from './pages/InsightsPage'
import KnowledgeSettingsPage from './pages/KnowledgeSettingsPage'
import AgentSettingsPage from './pages/AgentSettingsPage'
import DistributionTasksPage from './pages/DistributionTasksPage'
import DistributionChannelsPage from './pages/DistributionChannelsPage'
import DistributionLogsPage from './pages/DistributionLogsPage'
import DbAdminPage from './pages/DbAdminPage'
import RequireDeveloper from './components/RequireDeveloper'

export default function App() {
  useBrandConfig()
  const setSize = useMobileStore((s) => s.setSize)

  useEffect(() => {
    const onResize = () => setSize(window.innerWidth)
    setSize(window.innerWidth)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [setSize])

  const basename = (import.meta.env.VITE_BASE_PATH || '/').replace(/\/+$/, '') || '/'

  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="consultations" element={<ConsultationsPage />} />
          {/* 画像看板功能暂时隐藏(即将上线,功能待完善) */}
          {/* <Route path="profile" element={<ProfileDashboardPage />} /> */}
          <Route path="insights" element={<InsightsPage />} />
          <Route path="knowledge" element={<KnowledgeSettingsPage />} />
          <Route path="agent-settings" element={<AgentSettingsPage />} />
          <Route path="distribution/tasks" element={<DistributionTasksPage />} />
          <Route path="distribution/channels" element={<DistributionChannelsPage />} />
          <Route path="distribution/logs" element={<DistributionLogsPage />} />
          <Route
            path="db"
            element={
              <RequireDeveloper>
                <DbAdminPage />
              </RequireDeveloper>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
