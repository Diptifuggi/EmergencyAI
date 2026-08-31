import authApi from '../api/authApi'

export default {
  login: (credentials) => authApi.login(credentials),
  refresh: (payload) => authApi.refresh(payload),
  logout: () => authApi.logout()
}
