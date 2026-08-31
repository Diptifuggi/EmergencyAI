import api from './axios'

export default {
  uploadFile: (formData) => api.post('/uploads', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}
