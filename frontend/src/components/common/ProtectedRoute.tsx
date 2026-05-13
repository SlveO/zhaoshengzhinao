import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'

export default function ProtectedRoute() {
  return useAuthStore((s) => s.isAuthenticated) ? <Outlet /> : <Navigate to="/login" />
}
