import healthApi from '../api/healthApi'

export default {
  health: () => healthApi.health(),
  healthDb: () => healthApi.healthDb()
}
