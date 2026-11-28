// @ts-nocheck
import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, User, Phone, HeartPulse, Siren, FileText, MapPin, ShieldAlert } from 'lucide-react'

import { getUserSummary } from '@/api/usersApi'
import { formatIST } from '@/lib/formatters'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['user-summary', id],
    queryFn: () => getUserSummary(id!),
    enabled: !!id,
  })

  if (isLoading) return <Loading />
  if (error || !data) return <ErrorMessage error={error || new Error('User not found')} />

  const { user, profile, emergency_contacts = [], sos_alerts = [], reports = [], track_sessions = [] } = data

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-lg bg-white border hover:bg-zinc-50"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-zinc-900">
            {profile?.full_name || user.username}
          </h1>
          <p className="text-xs text-zinc-500">
            {user.email} • Role: {user.role_name} • {user.is_active ? 'Active' : 'Disabled'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile & Medical Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <User className="w-4 h-4" /> Citizen Profile & Medical Info
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 text-sm">
            <div><span className="text-zinc-500">Phone:</span> {profile?.phone || 'Not provided'}</div>
            <div><span className="text-zinc-500">Alternate:</span> {profile?.alternate_phone || 'Not provided'}</div>
            <div><span className="text-zinc-500">Guardian:</span> {profile?.guardian_phone ? `${profile.guardian_phone} (${profile.guardian_relation || 'Guardian'})` : 'Not provided'}</div>
            <div><span className="text-zinc-500">Address:</span> {profile?.address || 'Not provided'}</div>
            <div className="flex gap-6 pt-2 border-t">
              <div><span className="text-zinc-500">Age:</span> {profile?.age ?? 'N/A'}</div>
              <div><span className="text-zinc-500">Blood:</span> <span className="font-bold text-red-600">{profile?.blood_group || 'unknown'}</span></div>
            </div>
            <div className="pt-2 border-t space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-xs text-red-600">
                <HeartPulse className="w-3.5 h-3.5" /> Medical Details ({profile?.medical_consent ? 'Consented' : 'No Consent'})
              </div>
              <div className="text-xs"><span className="text-zinc-500">Allergies:</span> {profile?.allergies || 'None / Not consented'}</div>
              <div className="text-xs"><span className="text-zinc-500">History:</span> {profile?.medical_history || 'None / Not consented'}</div>
            </div>
            {emergency_contacts.length > 0 && (
              <div className="pt-2 border-t">
                <div className="font-semibold text-xs mb-1">Emergency Contacts ({emergency_contacts.length})</div>
                {emergency_contacts.map((ec: any) => (
                  <div key={ec.id} className="text-xs flex justify-between py-0.5">
                    <span>{ec.name} ({ec.relation})</span>
                    <a href={`tel:${ec.phone}`} className="text-blue-600 hover:underline font-mono">{ec.phone}</a>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* SOS Alerts & Reports */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Siren className="w-4 h-4 text-red-600" /> SOS Alerts ({sos_alerts.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {sos_alerts.length === 0 ? (
                <p className="text-xs text-zinc-500">No SOS alerts for this user.</p>
              ) : (
                <div className="divide-y text-sm">
                  {sos_alerts.map((a: any) => (
                    <div
                      key={a.id}
                      onClick={() => navigate(`/sos/${a.id}`)}
                      className="py-2.5 flex items-center justify-between cursor-pointer hover:bg-zinc-50 px-2 rounded"
                    >
                      <div>
                        <span className="font-semibold uppercase text-xs">{a.alert_type.replace('_', ' ')}</span>
                        <span className="ml-2 text-xs px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded">
                          {a.service_category}
                        </span>
                        <p className="text-xs text-zinc-500">{formatIST(a.received_at)}</p>
                      </div>
                      <span className="text-xs font-bold uppercase px-2 py-1 rounded bg-zinc-100">{a.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" /> Voice / Text Reports ({reports.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {reports.length === 0 ? (
                <p className="text-xs text-zinc-500">No voice or text reports linked to this user.</p>
              ) : (
                <div className="divide-y text-sm">
                  {reports.map((r: any) => (
                    <div
                      key={r.id}
                      onClick={() => navigate(`/calls/${r.id}`)}
                      className="py-2.5 flex items-center justify-between cursor-pointer hover:bg-zinc-50 px-2 rounded"
                    >
                      <div className="min-w-0 pr-4">
                        <p className="font-medium truncate">{r.text_content || 'Voice report'}</p>
                        <p className="text-xs text-zinc-500">{formatIST(r.created_at)} • {r.location_address || 'No address'}</p>
                      </div>
                      <span className="text-xs font-semibold uppercase px-2 py-1 rounded bg-zinc-100 shrink-0">{r.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <MapPin className="w-4 h-4 text-purple-600" /> TrackMe Sessions ({track_sessions.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {track_sessions.length === 0 ? (
                <p className="text-xs text-zinc-500">No TrackMe sessions found.</p>
              ) : (
                <div className="divide-y text-sm">
                  {track_sessions.map((t: any) => (
                    <div
                      key={t.id}
                      onClick={() => navigate(`/track/${t.share_token}`)}
                      className="py-2.5 flex items-center justify-between cursor-pointer hover:bg-zinc-50 px-2 rounded"
                    >
                      <div>
                        <span className="font-medium text-xs">{t.duration_hours}h Session</span>
                        <p className="text-xs text-zinc-500">{formatIST(t.started_at)}</p>
                      </div>
                      <span className="text-xs font-bold uppercase px-2 py-1 rounded bg-purple-50 text-purple-700">{t.status}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
