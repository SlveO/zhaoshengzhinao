import api from './api'

export const recApi = {
  getRecommendations: () => api.get('/recommendations'),
}
