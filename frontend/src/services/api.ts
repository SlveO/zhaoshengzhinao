import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use((r) => r, async (error) => {
  if (error.response?.status === 401) {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        const { data } = await axios.post('/api/v1/auth/refresh', {}, { headers: { Authorization: `Bearer ${refresh}` } })
        localStorage.setItem('access_token', data.access_token)
        error.config.headers.Authorization = `Bearer ${data.access_token}`
        return api(error.config)
      } catch { localStorage.clear(); window.location.href = '/login' }
    }
  }
  return Promise.reject(error)
})

export default api
