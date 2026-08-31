import React from 'react'
import { useForm } from 'react-hook-form'
import uploadService from '../../services/uploadService'

export default function UploadCall() {
  const { register, handleSubmit } = useForm()
  const onSubmit = async (vals) => {
    const fd = new FormData()
    if (vals.file && vals.file[0]) fd.append('file', vals.file[0])
    try {
      await uploadService.uploadFile(fd)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="p-4 bg-white rounded shadow">
      <h2 className="font-semibold mb-2">Upload Call</h2>
      <input type="file" {...register('file')} />
      <div className="mt-3">
        <button className="py-2 px-4 bg-blue-600 text-white rounded">Upload</button>
      </div>
    </form>
  )
}
