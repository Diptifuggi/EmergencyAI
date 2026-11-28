// @ts-nocheck
import React from 'react'
import { Navigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

type Props = {
  children: React.ReactNode
  requiredRole?: string
  allowedRoles?: string[]
}

export default function ProtectedRoute({ children, requiredRole, allowedRoles }: Props) {
  const { isLoading, isAuthenticated, user } = useAuth()

  if (isLoading) {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />

  const userRole = ((user as any)?.role_name || '').toLowerCase()
  if (requiredRole && userRole !== requiredRole.toLowerCase()) {
    return <Navigate to="/unauthorized" replace />
  }
  if (allowedRoles && allowedRoles.length > 0) {
    const allowed = allowedRoles.map(r => r.toLowerCase())
    if (!allowed.includes(userRole)) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return <>{children}</>
}
