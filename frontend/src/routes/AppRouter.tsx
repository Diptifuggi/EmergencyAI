import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '@/layouts/MainLayout'
import Dashboard from '@/pages/Dashboard'
import EmergencyCalls from '@/pages/EmergencyCalls'
import EmergencyDetails from '@/pages/EmergencyDetails'
import DispatchCenter from '@/pages/DispatchCenter'
import IncidentMap from '@/pages/IncidentsMapPage'
import SOPManager from '@/pages/SOPManager'
import Analytics from '@/pages/Analytics'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import NotFound from '@/pages/NotFound'

export default function AppRouter() {
  // TODO: add auth guard if needed
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/" element={<MainLayout><Dashboard /></MainLayout>} />
      <Route path="/emergencies" element={<MainLayout><EmergencyCalls /></MainLayout>} />
      <Route path="/emergencies/:id" element={<MainLayout><EmergencyDetails /></MainLayout>} />
      <Route path="/dispatch" element={<MainLayout><DispatchCenter /></MainLayout>} />
      <Route path="/map" element={<MainLayout><IncidentMap /></MainLayout>} />
      <Route path="/sop" element={<MainLayout><SOPManager /></MainLayout>} />
      <Route path="/analytics" element={<MainLayout><Analytics /></MainLayout>} />
      <Route path="/404" element={<MainLayout><NotFound /></MainLayout>} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  )
}
