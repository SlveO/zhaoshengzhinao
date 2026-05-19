import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  const location = useLocation()

  if (!token) {
    const params = new URLSearchParams(location.search)
    const tenant = params.get('tenant')
    const target = tenant ? `/login?tenant=${tenant}` : '/login'
    return <Navigate to={target} state={{ from: location }} replace />
  }

  return <>{children}</>
}
