import api from './api'

export const recApi = {
  getRecommendations: () => api.get('/recommendations'),
  submitFeedback: (collegeName: string, majorName: string, feedbackType: string) =>
    api.post('/recommendations/feedback', {
      college_name: collegeName,
      major_name: majorName,
      feedback_type: feedbackType,
    }),
}
