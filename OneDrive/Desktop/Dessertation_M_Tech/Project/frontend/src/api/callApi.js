import api from './axios'

export default {
  list: (params) => api.get('/calls', { params }),
  get: (id) => api.get(`/calls/${id}`),
  upload: (formData) => api.post('/calls/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}
