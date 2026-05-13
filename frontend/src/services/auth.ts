import api from './api'

export const authApi = {
  login: (username: string, password: string) => api.post('/auth/login', { username, password }),
  register: (username: string, password: string, region: string, score: number, subjects: string) => api.post('/auth/register', { username, password, region, score, subjects }),
}
