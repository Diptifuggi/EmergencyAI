// @ts-nocheck
import React, { useCallback, useEffect, useRef, useState } from 'react'
import { UploadCloud } from 'lucide-react'
import { Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from '@/components/ui'
import callsApi from '@/api/callsApi'
import { toast } from 'react-hot-toast'

const MAX_SIZE = 50 * 1024 * 1024 // 50MB
const ALLOWED_EXT = ['wav','mp3','m4a','ogg']

export default function FileUploadDropzone({ callId, onComplete }) {
  const [drag, setDrag] = useState(false)
  const [state, setState] = useState('idle') // idle, validating, uploading, processing, done, error
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const inputRef = useRef(null)

  const validateFile = (file) => {
    if (!file) return { ok: false, reason: 'No file' }
    const ext = (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED_EXT.includes(ext)) return { ok: false, reason: 'Unsupported file type' }
    if (file.size > MAX_SIZE) return { ok: false, reason: 'File exceeds 50MB' }
    return { ok: true }
  }

  const handleFiles = useCallback(async (files) => {
    if (!files || files.length === 0) return
    const file = files[0]
    const v = validateFile(file)
    if (!v.ok) {
      toast.error(v.reason)
      setState('error')
      return
    }
    setState('uploading')
    setProgress(0)
    const controller = new AbortController()
    uploadControllerRef.current = controller
    try {
      const data = await callsApi.uploadAudio(
        callId,
        file,
        (evt) => { if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100)) },
        controller.signal,
      )
      setState('done')
      setResult(data)
      if (onComplete) onComplete(data)
    } catch (e) {
      if (e?.name === 'CanceledError' || e?.code === 'ERR_CANCELED') {
        toast.error('Upload canceled')
      } else {
        setState('error')
        toast.error(e?.message || 'Upload failed')
      }
    } finally {
      uploadControllerRef.current = null
    }
  }, [callId, onComplete])

  const uploadControllerRef = useRef(null)

  const cancelUpload = () => {
    if (uploadControllerRef.current) {
      try { uploadControllerRef.current.abort() } catch(e) {}
      uploadControllerRef.current = null
      setState('idle')
      setProgress(0)
    }
  }

  useEffect(() => {
    return () => { if (uploadControllerRef.current) uploadControllerRef.current.abort() }
  }, [])

  const onDrop = (e) => {
    e.preventDefault()
    setDrag(false)
    handleFiles(e.dataTransfer.files)
  }
  const onDragOver = (e) => { e.preventDefault(); setDrag(true) }
  const onDragLeave = (e) => { e.preventDefault(); setDrag(false) }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Audio</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragEnter={onDragOver}
          onDragLeave={onDragLeave}
          className={`w-full border-2 rounded p-6 flex flex-col items-center justify-center text-center cursor-pointer ${drag ? 'border-zinc-700 bg-zinc-50' : 'border-dashed border-zinc-300'}`}
          onClick={() => inputRef.current?.click()}
        >
          {state === 'uploading' ? (
            <div className="w-full">
              <div className="flex items-center justify-center mb-2"><UploadCloud className="h-10 w-10" /></div>
              <div className="text-sm mb-2">Uploading... {progress}%</div>
              <div className="w-full bg-gray-200 h-2 rounded"><div style={{ width: `${progress}%` }} className="h-2 bg-zinc-900" /></div>
              <div className="mt-3 flex justify-center"><Button variant="secondary" onClick={cancelUpload}>Cancel Upload</Button></div>
            </div>
          ) : state === 'processing' ? (
            <div>
              <div className="flex items-center justify-center mb-2"><UploadCloud className="h-10 w-10 animate-pulse" /></div>
              <div className="text-sm">Processing audio... this may take a few seconds</div>
            </div>
          ) : state === 'done' ? (
            <div className="flex flex-col items-center">
              <div className="text-sm font-semibold mb-2">Audio upload complete</div>
              <Button onClick={() => { if (onComplete) onComplete(result); }}>View Call</Button>
            </div>
          ) : state === 'error' ? (
            <div className="text-red-600">Upload failed. <Button onClick={() => setState('idle')}>Retry</Button></div>
          ) : (
            <div>
              <div className="flex items-center justify-center mb-2"><UploadCloud className="h-10 w-10" /></div>
              <div className="text-sm">Drop audio file here</div>
              <div className="text-xs text-gray-500 mt-2">or click to browse</div>
              <div className="text-xs text-gray-500 mt-2">Supported: .wav .mp3 .m4a .ogg • Max 50MB</div>
            </div>
          )}
          <input ref={inputRef} type="file" accept="audio/*" className="hidden" onChange={(e)=>handleFiles(e.target.files)} />
        </div>
      </CardContent>
    </Card>
  )
}
