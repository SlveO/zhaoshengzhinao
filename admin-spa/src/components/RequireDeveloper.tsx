import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

export default function RequireDeveloper({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user?.is_developer) {
    return <Navigate to="/dashboard" replace />
  }
  return <>{children}</>
}
