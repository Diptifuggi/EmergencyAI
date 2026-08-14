// @ts-nocheck
import { useQuery } from '@tanstack/react-query'
import * as callsApi from '@/api/callsApi'

export default function useCallPipelineStatus(callId?: string | null) {
  const query = useQuery({
    queryKey: ['call-pipeline', callId],
    queryFn: async () => {
      if (!callId) return null
      const data = await callsApi.getCall(callId)
      return data
    },
    enabled: !!callId,
    refetchInterval: (data: any) => {
      if (!data) return 2000
      const status = data.pipeline_status || (data.pipeline && data.pipeline.status) || ''
      const stop = ['Completed', 'Failed', 'Resolved']
      return stop.includes(status) ? false : 2000
    },
    refetchOnWindowFocus: false,
  })

  return {
    data: query.data,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  }
}
