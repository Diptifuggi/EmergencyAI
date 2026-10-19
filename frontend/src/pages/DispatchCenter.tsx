// @ts-nocheck
import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getEmergencies } from '@/api/emergencyApi'
import { categoryForCall, locationForCall } from '@/types/emergency'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'
import { toast } from 'react-hot-toast'

export default function DispatchCenter() {
  const { data: calls = [], isLoading, error } = useQuery({
    queryKey: ['emergency-calls'],
    queryFn: () => getEmergencies({ limit: 200, offset: 0 }),
    refetchInterval: 10000,
  })
  const data = calls
    .filter((call) => ['received', 'pending_transcription', 'analyzing'].includes(call.status))
    .map((call) => ({ ...call, category: categoryForCall(call), location: locationForCall(call) }))
  const [selected, setSelected] = useState(null)

  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  return (
    <div>
      <Card title="Dispatch Center">
        <div className="grid grid-cols-1 gap-4">
          {data?.map(call => (
            <div key={call.id} className="p-3 border rounded flex justify-between items-center">
              <div>
                <div className="font-semibold">{call.id} — {call.category}</div>
                <div className="text-sm text-muted-foreground">{call.location}</div>
              </div>
              <div className="flex gap-2">
                <select onChange={(e)=>setSelected(e.target.value)} className="border p-2 rounded">
                  <option value="">Assign Dept</option>
                  <option>Police</option>
                  <option>Fire</option>
                  <option>Ambulance</option>
                  <option>Women Team</option>
                  <option>Child Protection Team</option>
                </select>
                <button className="px-3 py-1 bg-black text-white rounded" onClick={()=>toast.error('Dispatch assignment is not available from the current backend.')}>Dispatch</button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
