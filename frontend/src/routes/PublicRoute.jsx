import React from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import AuthLayout from '../components/layout/AuthLayout'

export default function PublicRoute() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (user) return <Navigate to="/dashboard" replace />

  return (
    <AuthLayout>
      <Outlet />
    </AuthLayout>
  )
}
