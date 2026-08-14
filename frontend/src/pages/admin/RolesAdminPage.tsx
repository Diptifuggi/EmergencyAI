// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import axiosClient from '@/api/axiosClient'
import { Card, CardHeader, CardTitle, CardContent, Badge, Button } from '@/components/ui'
import { ShieldAlert, Radio, Shield, Flame, HeartPulse, BarChart3 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const ICON_MAP = {
  Admin: ShieldAlert,
  Dispatcher: Radio,
  Police: Shield,
  Fire: Flame,
  Ambulance: HeartPulse,
  Analyst: BarChart3,
}

export default function RolesAdminPage(){
  const { data } = useQuery({ queryKey: ['roles'], queryFn: async ()=> { const r = await axiosClient.get('/roles'); return r.data } })
  const roles = data || []
  const navigate = useNavigate()

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Roles & Permissions</h1>
          <div className="text-sm text-gray-600">Roles are seeded at deployment — contact admin to modify</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {!data ? (
          new Array(6).fill(0).map((_, i) => (
            <div key={i} className="h-28 bg-gray-100 animate-pulse rounded" />
          ))
        ) : roles.length === 0 ? (
          <div className="col-span-3 p-8 text-center text-gray-600">No roles found</div>
        ) : (
          roles.map((r: any) => {
            const Icon = ICON_MAP[r.name] || Shield
            return (
              <Card key={r.name}>
                <CardContent>
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-full bg-zinc-900 text-white flex items-center justify-center"><Icon className="w-6 h-6" /></div>
                    <div>
                      <div className="text-xl font-semibold">{r.name}</div>
                      <div className="text-sm text-gray-600 mt-1">{r.description}</div>
                      <div className="mt-3 flex items-center gap-2">
                        <Badge className="bg-gray-100 text-gray-700">{r.user_count || 0} users</Badge>
                        <div className="text-xs text-gray-500">{r.created_at ? new Date(r.created_at).toLocaleDateString() : ''}</div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 text-right"><Button onClick={() => navigate(`/admin/users?role=${encodeURIComponent(r.name)}`)}>View Users →</Button></div>
                </CardContent>
              </Card>
            )
          })
        )}
      </div>
    </div>
  )
}
