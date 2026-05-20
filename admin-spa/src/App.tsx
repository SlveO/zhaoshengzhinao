import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useBrandConfig } from './hooks/useBrandConfig'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardLayout from './components/DashboardLayout'
import LoginPage from './pages/LoginPage'
import ProfileDashboardPage from './pages/ProfileDashboardPage'
import BrandSettingsPage from './pages/BrandSettingsPage'
import KnowledgeSettingsPage from './pages/KnowledgeSettingsPage'
import InsightsPage from './pages/InsightsPage'
import AgentSettingsPage from './pages/AgentSettingsPage'
import DashboardPage from './pages/DashboardPage'
import ModuleSettingsPage from './pages/ModuleSettingsPage'
import ReportsPage from './pages/ReportsPage'

export default function App() {
  useBrandConfig()

  return (
    <BrowserRouter>
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
          <Route path="profile" element={<ProfileDashboardPage />} />
          <Route path="brand" element={<BrandSettingsPage />} />
          <Route path="knowledge" element={<KnowledgeSettingsPage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="agent-settings" element={<AgentSettingsPage />} />
          <Route path="modules" element={<ModuleSettingsPage />} />
          <Route path="reports" element={<ReportsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
