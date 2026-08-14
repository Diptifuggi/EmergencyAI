import React from 'react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="max-w-4xl mx-auto text-center py-20">
      <h1 className="text-3xl font-bold mb-4">Page not found</h1>
      <p className="mb-6">We couldn't find the page you're looking for.</p>
      <Link to="/" className="px-4 py-2 bg-black text-white rounded-md">Go home</Link>
    </div>
  )
}
