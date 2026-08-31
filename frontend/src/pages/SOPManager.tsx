// @ts-nocheck
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAnalytics } from '@/api/analyticsApi'
import Card from '@/components/common/Card'
import Loading from '@/components/common/Loading'
import ErrorMessage from '@/components/common/ErrorMessage'

const categories = ["Road Accident","Fire","Medical Emergency","Women Safety","Child Abuse","Cyber Crime","Natural Disaster"]

export default function SOPManager() {
  const { data, isLoading, error } = useQuery({ queryKey: ['sop'], queryFn: async () => {
    // For now reuse analytics endpoint for demo; in real API use /sop
    const res = await getAnalytics()
    return res
  } })

  if (isLoading) return <Loading />
  if (error) return <ErrorMessage error={error} />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">SOP Manager</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {categories.map(cat => (
          <Card key={cat} title={cat}>
            <ul className="list-disc ml-5">
              {(data?.sop?.[cat] || ['Follow local protocol']).map((step: any, idx: number) => (
                <li key={idx}>{step}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  )
}
