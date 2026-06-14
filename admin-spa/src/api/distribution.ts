import api from './client'
import type {
  DistributionChannel, DistributionFile, DistributionTask, DistributionLog,
} from '../types'

export const distributionApi = {
  // ── Channels ──
  listChannels: (page = 1, pageSize = 20) =>
    api.get('/distribution/channels', { params: { page, page_size: pageSize } }),

  createChannel: (data: { name: string; channel_type: string; webhook_url: string; config?: Record<string, any> }) =>
    api.post('/distribution/channels', data),

  getChannel: (id: string) =>
    api.get(`/distribution/channels/${id}`),

  updateChannel: (id: string, data: Record<string, any>) =>
    api.put(`/distribution/channels/${id}`, data),

  deleteChannel: (id: string) =>
    api.delete(`/distribution/channels/${id}`),

  testChannel: (id: string) =>
    api.post(`/distribution/channels/${id}/test`),

  // ── Files ──
  uploadFile: (file: File, onProgress?: (pct: number) => void) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/distribution/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      },
    })
  },

  listFiles: (page = 1, pageSize = 20) =>
    api.get('/distribution/files', { params: { page, page_size: pageSize } }),

  deleteFile: (id: string) =>
    api.delete(`/distribution/files/${id}`),

  // ── Tasks ──
  listTasks: (page = 1, pageSize = 20, status?: string) =>
    api.get('/distribution/tasks', { params: { page, page_size: pageSize, status } }),

  createTask: (data: {
    name: string; file_id: string; channel_id: string;
    schedule_type: string; schedule_config?: Record<string, any>;
    scheduled_at?: string; message_text?: string;
  }) => api.post('/distribution/tasks', data),

  getTask: (id: string) =>
    api.get(`/distribution/tasks/${id}`),

  updateTask: (id: string, data: Record<string, any>) =>
    api.put(`/distribution/tasks/${id}`, data),

  deleteTask: (id: string) =>
    api.delete(`/distribution/tasks/${id}`),

  triggerTask: (id: string) =>
    api.post(`/distribution/tasks/${id}/run`),

  pauseTask: (id: string) =>
    api.post(`/distribution/tasks/${id}/pause`),

  resumeTask: (id: string) =>
    api.post(`/distribution/tasks/${id}/resume`),

  // ── Logs ──
  listLogs: (page = 1, pageSize = 20, filters?: {
    task_id?: string; channel_id?: string; status?: string;
  }) => api.get('/distribution/logs', { params: { page, page_size: pageSize, ...filters } }),
}
