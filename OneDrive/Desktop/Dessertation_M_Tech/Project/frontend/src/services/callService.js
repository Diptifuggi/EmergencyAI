import callApi from '../api/callApi'

export default {
  list: (params) => callApi.list(params),
  get: (id) => callApi.get(id),
  upload: (form) => callApi.upload(form)
}
