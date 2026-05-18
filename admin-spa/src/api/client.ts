import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

function getTenantSlug(): string | null {
  const params = new URLSearchParams(window.location.search)
  return params.get('tenant') || localStorage.getItem('tenantSlug')
}

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const slug = getTenantSlug()
  if (slug) {
    config.headers['X-Tenant'] = slug
  }
  const token = useAuthStore.getState().token
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  },
)

export default api
