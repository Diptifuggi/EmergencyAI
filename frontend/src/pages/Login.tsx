// @ts-nocheck
import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { login } from '@/api/authApi'
import { useNavigate, useLocation } from 'react-router-dom'

export default function Login() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState<any>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const successMessage = (location as any).state?.message

  const mutation = useMutation({
    mutationFn: ({ email, password }: any) => login(email, password),
    onSuccess: () => {
      navigate('/dashboard')
    },
    onError: (e: any) => {
      const errorMsg = e?.response?.data?.detail || e?.message || 'Login failed'
      setError(errorMsg)
    },
  })

  function submit(e: any) {
    e.preventDefault()
    setError(null)
    
    if (!form.email || !form.password) {
      setError('Please enter both email and password')
      return
    }
    
    mutation.mutate({ email: form.email, password: form.password })
  }

  return (
    <div className="max-w-md mx-auto mt-20">
      <h1 className="text-2xl font-bold mb-4">Sign in</h1>
      
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded mb-4">
          {successMessage}
        </div>
      )}
      
      <form onSubmit={submit} className="space-y-3">
        <div>
          <input 
            aria-label="email" 
            value={form.email} 
            onChange={(e) => setForm({ ...form, email: e.target.value })} 
            placeholder="Email" 
            type="email"
            className="w-full border p-2 rounded" 
          />
        </div>
        
        <div>
          <input 
            aria-label="password" 
            value={form.password} 
            onChange={(e) => setForm({ ...form, password: e.target.value })} 
            placeholder="Password" 
            type="password" 
            className="w-full border p-2 rounded" 
          />
        </div>
        
        <button 
          type="submit" 
          disabled={mutation.isPending}
          className="w-full px-4 py-2 bg-black text-white rounded disabled:bg-gray-400"
        >
          {mutation.isPending ? 'Signing in...' : 'Sign in'}
        </button>
      </form>
      
      {error && (
        <div className="text-red-600 mt-4 p-3 bg-red-50 rounded">
          {error}
        </div>
      )}
      
      <div className="text-sm text-gray-600 mt-4">
        Don't have an account? <button onClick={() => navigate('/register')} className="text-blue-600 hover:underline">Create one</button>
      </div>
    </div>
  )
}
