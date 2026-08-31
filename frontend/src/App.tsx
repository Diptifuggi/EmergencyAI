// @ts-nocheck
import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import Layout from '@/components/layout/Layout'
import ErrorBoundary from '@/components/ErrorBoundary'
import Dashboard from '@/pages/Dashboard'
import EmergencyCalls from '@/pages/EmergencyCalls'
import EmergencyDetails from '@/pages/EmergencyDetails'
import CallViewerPage from '@/pages/CallViewerPage'
import DispatchCenter from '@/pages/DispatchCenter'
import IncidentsMapPage from '@/pages/IncidentsMapPage'
import IncidentDetailPage from '@/pages/IncidentDetailPage'
import SOPManager from '@/pages/SOPManager'
import Analytics from '@/pages/Analytics'
import Login from '@/pages/LoginPage'
import Register from '@/pages/Register'
import NotFound from '@/pages/NotFoundPage'
import UsersAdmin from '@/pages/admin/UsersAdmin'
import RolesAdmin from '@/pages/admin/RolesAdmin'
import AuditLogs from '@/pages/admin/AuditLogs'
import NewCallDialog from '@/components/calls/NewCallDialog'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      refetchOnWindowFocus: false,
      retry: (failureCount: number, error: any) => {
        const status = error?.response?.status
        if (status === 401 || status === 403) return false
        return failureCount < 1
      }
    }
  }
})

function AppRoutes(){
  return (
    <Routes>
      <Route path="/register" element={<Register />} />
      <Route path="/signup" element={<Register />} />
      <Route path="/login" element={<LoginWrapper />} />

      <Route path="/" element={<ProtectedRoute><ErrorBoundary><Layout /></ErrorBoundary></ProtectedRoute>}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="calls" element={<EmergencyCalls />} />
        <Route path="calls/:id" element={<CallViewerPage />} />
          <Route path="incidents" element={<IncidentsMapPage />} />
          <Route path="incidents (map)" element={<Navigate to="/incidents" replace />} />
          <Route path="incidents/:id" element={<IncidentDetailPage />} />
          <Route path="incidents (map)/:id" element={<Navigate to="/incidents/:id" replace />} />
        <Route path="dispatch" element={<DispatchCenter />} />
        <Route path="sop" element={<SOPManager />} />
        <Route path="analytics" element={<Analytics />} />

        <Route path="admin/users" element={<UsersAdmin />} />
        <Route path="admin/roles" element={<RolesAdmin />} />
        <Route path="admin/audit" element={<AuditLogs />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

function LoginWrapper(){
  const { isAuthenticated } = useAuth()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  return <Login />
}

export default function App(){
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
          <Toaster position="top-right" />
          <NewCallDialog />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
