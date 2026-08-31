import api from './axios'

export default {
  health: () => api.get('/health'),
  healthDb: () => api.get('/health/db')
}
