import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useBrandConfig } from './hooks/useBrandConfig'
import ProtectedRoute from './components/ProtectedRoute'
import DashboardLayout from './components/DashboardLayout'
import LoginPage from './pages/LoginPage'
import FunnelPage from './pages/FunnelPage'
import ProfileDashboardPage from './pages/ProfileDashboardPage'
import BrandSettingsPage from './pages/BrandSettingsPage'
import KnowledgeSettingsPage from './pages/KnowledgeSettingsPage'
import InsightsPage from './pages/InsightsPage'

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
          <Route index element={<Navigate to="/funnel" replace />} />
          <Route path="funnel" element={<FunnelPage />} />
          <Route path="profile" element={<ProfileDashboardPage />} />
          <Route path="brand" element={<BrandSettingsPage />} />
          <Route path="knowledge" element={<KnowledgeSettingsPage />} />
          <Route path="insights" element={<InsightsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
