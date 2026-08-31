import uploadApi from '../api/uploadApi'

export default {
  uploadFile: (form) => uploadApi.uploadFile(form)
}
