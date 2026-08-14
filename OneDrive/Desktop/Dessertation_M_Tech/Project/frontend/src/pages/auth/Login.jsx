import React from 'react'
import { useForm } from 'react-hook-form'
import useAuth from '../../hooks/useAuth'

export default function Login() {
  const { register, handleSubmit } = useForm()
  const { login } = useAuth()

  const onSubmit = async (vals) => {
    try {
      await login(vals)
      // navigation handled by auth context + routes
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <h2 className="text-xl font-bold mb-4">Sign in</h2>
      <div className="mb-3">
        <input {...register('email')} placeholder="Email" className="w-full p-2 border rounded bg-[rgba(255,255,255,0.02)]" />
      </div>
      <div className="mb-3">
        <input {...register('password')} type="password" placeholder="Password" className="w-full p-2 border rounded" />
      </div>
      <button className="w-full py-2 bg-blue-600 text-white rounded">Login</button>
    </form>
  )
}
