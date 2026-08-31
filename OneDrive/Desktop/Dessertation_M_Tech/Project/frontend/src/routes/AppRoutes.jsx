import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import PrivateRoute from './PrivateRoute'
import PublicRoute from './PublicRoute'
import Dashboard from '../pages/dashboard/Dashboard'
import Analytics from '../pages/dashboard/Analytics'
import Login from '../pages/auth/Login'
import CallsList from '../pages/calls/CallsList'
import CallDetails from '../pages/calls/CallDetails'
import IncidentList from '../pages/incidents/IncidentList'
import IncidentDetails from '../pages/incidents/IncidentDetails'
import UserList from '../pages/users/UserList'
import Settings from '../pages/settings/Settings'

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicRoute />}> 
        <Route path="/login" element={<Login />} />
      </Route>

      <Route element={<PrivateRoute />}> 
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/calls" element={<CallsList />} />
        <Route path="/calls/:id" element={<CallDetails />} />
        <Route path="/incidents" element={<IncidentList />} />
        <Route path="/incidents/:id" element={<IncidentDetails />} />
        <Route path="/users" element={<UserList />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
