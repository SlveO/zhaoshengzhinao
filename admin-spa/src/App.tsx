import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useBrandConfig } from './hooks/useBrandConfig'
import { useMobileStore } from './stores/mobileStore'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardLayout from './components/DashboardLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import LeadWorkbenchPage from './pages/LeadWorkbenchPage'
import ConsultationsPage from './pages/ConsultationsPage'
import ProfileDashboardPage from './pages/ProfileDashboardPage'
import InsightsPage from './pages/InsightsPage'
import ReportsPage from './pages/ReportsPage'
import ChannelsPage from './pages/ChannelsPage'
import KnowledgeSettingsPage from './pages/KnowledgeSettingsPage'
import BrandSettingsPage from './pages/BrandSettingsPage'
import AgentSettingsPage from './pages/AgentSettingsPage'
import ModuleSettingsPage from './pages/ModuleSettingsPage'

export default function App() {
  useBrandConfig()
  const setSize = useMobileStore((s) => s.setSize)

  useEffect(() => {
    const onResize = () => setSize(window.innerWidth)
    setSize(window.innerWidth)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [setSize])

  return (
    <BrowserRouter basename="/admin">
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
          <Route path="leads" element={<LeadWorkbenchPage />} />
          <Route path="consultations" element={<ConsultationsPage />} />
          <Route path="profile" element={<ProfileDashboardPage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="channels" element={<ChannelsPage />} />
          <Route path="knowledge" element={<KnowledgeSettingsPage />} />
          <Route path="brand" element={<BrandSettingsPage />} />
          <Route path="agent-settings" element={<AgentSettingsPage />} />
          <Route path="modules" element={<ModuleSettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
