// @ts-nocheck
import React, { useState } from 'react'
import { Button, Card, CardHeader, CardTitle, CardContent, Input } from '@/components/ui'
import callsApi from '@/api/callsApi'
import FileUploadDropzone from './FileUploadDropzone'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'

export default function NewCallDialog() {
  const [open, setOpen] = useState(false)
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({ caller_name: '', caller_phone: '', started_at: new Date().toISOString().slice(0,16), latitude: '', longitude: '' })
  const navigate = useNavigate()

  const createMutation = useMutation({
    mutationFn: (data) => callsApi.createCall(data),
    onSuccess: (data) => {
      if (data?.id) {
        setForm(prev => ({ ...prev, id: data.id }))
        setStep(2)
      } else {
        toast.error('Failed to create call')
      }
    },
    onError: (e) => toast.error(e?.message || 'Failed to create call')
  })

  const handleCreate = async (e) => {
    e.preventDefault()
    createMutation.mutate({
      caller_name: form.caller_name,
      caller_phone: form.caller_phone,
      started_at: form.started_at,
      latitude: form.latitude || null,
      longitude: form.longitude || null,
    })
  }

  React.useEffect(() => {
    if (!open) return
    // attempt to auto-fill lat/lng when opening the dialog
    if (navigator && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((pos) => {
        const lat = pos.coords.latitude
        const lng = pos.coords.longitude
        setForm(f => ({ ...f, latitude: f.latitude || String(lat), longitude: f.longitude || String(lng) }))
      }, () => {}, { timeout: 5000 })
    }
  }, [open])

  const handleUploadComplete = (res) => {
    const id = form.id
    if (id) {
      setOpen(false)
      navigate(`/calls/${id}`)
    }
  }

  React.useEffect(() => {
    const handler = () => setOpen(true)
    window.addEventListener('openNewCallDialog', handler)
    return () => window.removeEventListener('openNewCallDialog', handler)
  }, [])

  return (
    <div>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded w-full max-w-2xl p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">New Emergency Call</h3>
              <div>
                <Button variant="ghost" onClick={() => setOpen(false)}>Close</Button>
              </div>
            </div>

            {step === 1 && (
              <form onSubmit={handleCreate} className="space-y-3">
                <div>
                  <label className="text-sm">Caller Name</label>
                  <Input value={form.caller_name} onChange={(e)=>setForm({...form, caller_name: e.target.value})} required />
                </div>
                <div>
                  <label className="text-sm">Caller Phone</label>
                  <Input value={form.caller_phone} onChange={(e)=>setForm({...form, caller_phone: e.target.value})} required />
                </div>
                <div>
                  <label className="text-sm">Call Start</label>
                  <Input type="datetime-local" value={form.started_at} onChange={(e)=>setForm({...form, started_at: e.target.value})} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-sm">Latitude</label>
                    <Input value={form.latitude} onChange={(e)=>setForm({...form, latitude: e.target.value})} />
                  </div>
                  <div>
                    <label className="text-sm">Longitude</label>
                    <Input value={form.longitude} onChange={(e)=>setForm({...form, longitude: e.target.value})} />
                  </div>
                </div>
                <div className="flex space-x-2">
                  <Button type="submit">Create Call</Button>
                  <Button variant="secondary" onClick={()=>{ setOpen(false) }}>Cancel</Button>
                </div>
              </form>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="text-sm text-gray-600">Upload audio for this call (optional). You may skip and continue to call details.</div>
                <FileUploadDropzone callId={form.id} onComplete={handleUploadComplete} />
                <div className="flex justify-end space-x-2">
                  <Button onClick={()=>{ setOpen(false); navigate(`/calls/${form.id}`) }}>Skip & View Call</Button>
                </div>
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  )
}
