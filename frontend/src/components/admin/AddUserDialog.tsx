// @ts-nocheck
import React, { useState } from 'react'
import axiosClient from '@/api/axiosClient'
import { Button, Input, Select } from '@/components/ui'
import { toastSuccess, toastError } from '@/lib/toast'
import { useMutation } from '@tanstack/react-query'

const ROLES = ['Admin','Dispatcher','Police','Fire','Ambulance','Analyst']

export default function AddUserDialog({ open = true, onClose }){
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '', role_name: 'Dispatcher', is_active: true })
  const [errors, setErrors] = useState({})

  const mutation = useMutation({
    mutationFn: (payload) => axiosClient.post('/users', payload),
    onSuccess: () => { toastSuccess('User created'); if (onClose) onClose() },
    onError: (e) => {
      const data = e?.response?.data
      if (data?.errors) setErrors(data.errors)
      toastError(e?.response?.data?.detail || e?.message || 'Failed to create user')
    }
  })

  function handleSubmit(e){
    e.preventDefault()
    setErrors({})
    // basic validation
    if (!form.full_name || !form.email || !form.password) {
      const err = {}
      if (!form.full_name) err.full_name = 'Required'
      if (!form.email) err.email = 'Required'
      if (!form.password) err.password = 'Required'
      setErrors(err)
      return
    }
    mutation.mutate(form)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Add User</h3>
          <button onClick={onClose} className="text-sm text-gray-500">Close</button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="text-sm">Full Name</label>
            <Input value={form.full_name} onChange={(e)=>setForm({...form, full_name: e.target.value})} />
            {errors.full_name && <div className="text-xs text-red-600">{errors.full_name}</div>}
          </div>
          <div>
            <label className="text-sm">Email</label>
            <Input value={form.email} onChange={(e)=>setForm({...form, email: e.target.value})} />
            {errors.email && <div className="text-xs text-red-600">{errors.email}</div>}
          </div>
          <div>
            <label className="text-sm">Phone</label>
            <Input value={form.phone} onChange={(e)=>setForm({...form, phone: e.target.value})} />
            {errors.phone && <div className="text-xs text-red-600">{errors.phone}</div>}
          </div>
          <div>
            <label className="text-sm">Password</label>
            <Input type="password" value={form.password} onChange={(e)=>setForm({...form, password: e.target.value})} />
            {errors.password && <div className="text-xs text-red-600">{errors.password}</div>}
          </div>
          <div>
            <label className="text-sm">Role</label>
            <Select value={form.role_name} onChange={(e)=>setForm({...form, role_name: e.target.value})}>
              {ROLES.map(r=> <option key={r} value={r}>{r}</option>)}
            </Select>
          </div>
          <div className="flex items-center justify-between">
            <div className="text-sm">Active</div>
            <input type="checkbox" checked={form.is_active} onChange={(e)=>setForm({...form, is_active: e.target.checked})} />
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="secondary" onClick={onClose} disabled={mutation.isLoading}>Cancel</Button>
            <Button type="submit" className="bg-black text-white" disabled={mutation.isLoading}>{mutation.isLoading ? 'Creating...' : 'Create'}</Button>
          </div>
        </form>
      </div>
    </div>
  )
}
