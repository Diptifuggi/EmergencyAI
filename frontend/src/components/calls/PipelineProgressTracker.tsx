// @ts-nocheck
import React, { useMemo } from 'react'
import { CheckCircle2, Loader2, Circle } from 'lucide-react'
import useCallPipelineStatus from '@/hooks/useCallPipelineStatus'
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui'

const STEPS = [
  { key: 'uploaded', title: 'Uploaded', desc: 'File received' },
  { key: 'transcribing', title: 'Transcribing', desc: 'Converting audio to text' },
  { key: 'classifying', title: 'Classifying', desc: 'Categorizing incident type' },
  { key: 'scoring', title: 'Scoring Severity', desc: 'Estimating severity score' },
  { key: 'correlating', title: 'Correlating Incident', desc: 'Linking related calls' },
]

export default function PipelineProgressTracker({ callId }) {
  const { data } = useCallPipelineStatus(callId)
  const status = data?.pipeline_status || data?.pipeline?.status || data?.status || ''

  const activeStep = useMemo(() => {
    if (!status) return 0
    const s = status.toLowerCase()
    if (s.includes('trans')) return 1
    if (s.includes('class')) return 2
    if (s.includes('score') || s.includes('scor')) return 3
    if (s.includes('correl') || s.includes('incident')) return 4
    if (s.includes('complete') || s.includes('scored') || s.includes('resolved')) return 5
    return 0
  }, [status])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline Progress</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {STEPS.map((step, i) => {
            const done = i < activeStep
            const active = i === activeStep
            return (
              <div key={step.key} className="flex items-start gap-3">
                <div className="w-8 h-8 flex items-center justify-center">
                  {done ? <CheckCircle2 className="text-green-600" /> : active ? <Loader2 className="animate-spin" /> : <Circle className="text-gray-400" />}
                </div>
                <div>
                  <div className="font-medium">{step.title} {active && <Badge className="ml-2">Active</Badge>}</div>
                  <div className="text-sm text-gray-500">{step.desc}{active && step.key==='transcribing' ? ' — Transcribing... (est. 12s)' : ''}</div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
