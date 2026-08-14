import React from 'react'
import { Outlet, Navigate } from 'react-router-dom'
import useAuth from '../hooks/useAuth'
import DashboardLayout from '../components/layout/DashboardLayout'

export default function PrivateRoute() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />

  return (
    <DashboardLayout>
      <Outlet />
    </DashboardLayout>
  )
}
