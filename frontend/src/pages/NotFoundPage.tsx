import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <div className="w-full h-full flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl font-bold">404</div>
        <div className="mt-2 text-lg">Page not found</div>
        <div className="mt-4">
          <button onClick={()=> navigate(-1)} className="px-4 py-2 bg-black text-white rounded">Go back</button>
        </div>
      </div>
    </div>
  )
}
