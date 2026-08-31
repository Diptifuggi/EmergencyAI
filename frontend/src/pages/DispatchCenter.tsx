// @ts-nocheck
import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getEmergencies } from '@/api/emergencyApi'
import { createDispatch } from '@/api/dispatchApi'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'
import Card from '@/components/common/Card'

export default function DispatchCenter() {
  const qc = useQueryClient()
  const { data, isLoading, error } = useQuery({ queryKey: ['emergencies'], queryFn: () => getEmergencies({ status: 'Processing' }) })
  const mutation = useMutation({ mutationFn: createDispatch, onSuccess: () => qc.invalidateQueries({ queryKey: ['emergencies'] }) })
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
                <button className="px-3 py-1 bg-black text-white rounded" onClick={()=>mutation.mutate({ call_id: call.id, department: selected })}>Dispatch</button>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
