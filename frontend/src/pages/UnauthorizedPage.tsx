import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function UnauthorizedPage() {
  const navigate = useNavigate()
  return (
    <div className="w-full h-full flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl font-bold">403</div>
        <div className="mt-2 text-lg">You are not authorized to view this page</div>
        <div className="mt-4">
          <button onClick={()=> navigate('/dashboard')} className="px-4 py-2 bg-black text-white rounded">Return to Dashboard</button>
        </div>
      </div>
    </div>
  )
}
