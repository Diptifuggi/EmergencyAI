import api from './axios'

export default {
  login: (payload) => api.post('/auth/login', payload),
  refresh: (refreshToken) => api.post('/auth/refresh', refreshToken),
  logout: () => api.post('/auth/logout')
}
