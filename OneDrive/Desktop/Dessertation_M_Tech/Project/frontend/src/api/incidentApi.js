import api from './axios'

export default {
  list: (params) => api.get('/incidents', { params }),
  get: (id) => api.get(`/incidents/${id}`),
  create: (payload) => api.post('/incidents', payload)
}
