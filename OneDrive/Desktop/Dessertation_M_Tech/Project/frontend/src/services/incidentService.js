import incidentApi from '../api/incidentApi'

export default {
  list: (params) => incidentApi.list(params),
  get: (id) => incidentApi.get(id),
  create: (payload) => incidentApi.create(payload)
}
