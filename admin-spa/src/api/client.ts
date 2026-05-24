import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

function getTenantSlug(): string | null {
  const params = new URLSearchParams(window.location.search)
  return params.get('tenant') || localStorage.getItem('tenantSlug')
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
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
  (response) => {
    // Cloudflare Pages _redirects 会劫持 API 请求返回 SPA 的 index.html，
    // 此时 response.data 是 HTML 字符串而非 JSON 对象，主动 reject 以便
    // 页面 catch handler 回退到 mock 数据。
    if (typeof response.data === 'string' && /^\s*<!doctype/i.test(response.data)) {
      return Promise.reject(new Error('API 不可用，当前为演示模式'))
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  },
)

export default api
