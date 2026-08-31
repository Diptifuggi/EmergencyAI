// @ts-nocheck
import React, { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import callsApi from '@/api/callsApi'
import axiosClient from '@/api/axiosClient'
import useCallPipelineStatus from '@/hooks/useCallPipelineStatus'
import { SOP_ACTIONS, DEPARTMENTS } from '@/lib/constants'
import formatters from '@/lib/formatters'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Button,
  Badge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Input,
  Select,
  Textarea,
  Skeleton,
} from '@/components/ui'
import FileUploadDropzone from '@/components/calls/FileUploadDropzone'
import PipelineProgressTracker from '@/components/calls/PipelineProgressTracker'

export default function CallDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: pipelineData, isLoading: pipelineLoading, refetch: refetchPipeline } = useCallPipelineStatus(id)

  const { data: call, isLoading, refetch } = useQuery({
    queryKey: ['call', id],
    queryFn: () => callsApi.getCall(id),
    enabled: !!id,
    refetchInterval: 15000,
  })

  const lastFive = useQuery({ queryKey: ['calls', 'recent'], queryFn: () => callsApi.listCalls({ page_size: 5 }), refetchInterval: 15000 })

  const runPipelineMutation = useMutation({
    mutationFn: (callId) => callsApi.runPipeline(callId),
    onSuccess: () => { refetch(); refetchPipeline(); qc.invalidateQueries({ queryKey: ['call'] }) },
  })

  const [dispatchDept, setDispatchDept] = useState(DEPARTMENTS[0] || '')
  const [officer, setOfficer] = useState('')
  const [sopComments, setSopComments] = useState('')
  const [showUpload, setShowUpload] = useState(false)

  async function onDispatch() {
    try {
      await axiosClient.post(`/incidents/${id}/dispatch`, { department: dispatchDept, officer })
      qc.invalidateQueries({ queryKey: ['call', id] })
    } catch (e) {
      console.error(e)
    }
  }

  const pipelineSteps = useMemo(() => {
    const status = pipelineData || call || {}
    // Example step states
    return [
      { key: 'received', label: 'Call Received', state: 'Completed' },
      { key: 'audio', label: 'Audio Uploaded', state: status.audio_uploaded ? 'Completed' : 'Pending' },
      { key: 'transcribing', label: 'Transcribing', state: status.transcribing ? 'InProgress' : (status.transcribed ? 'Completed' : 'Pending') },
      { key: 'classifying', label: 'Classifying', state: status.classifying ? 'InProgress' : (status.classified ? 'Completed' : 'Pending') },
      { key: 'severity', label: 'Severity Scored', state: status.severity_scored ? 'Completed' : 'Pending' },
      { key: 'correlate', label: 'Incident Correlated', state: status.correlated ? 'Completed' : 'Pending' },
    ]
  }, [pipelineData, call])

  return (
    <div className="p-4">
      <div className="grid grid-cols-[280px_1fr_300px] gap-4">
        {/* LEFT COLUMN */}
        <div className="space-y-4">
          <Card>
            <div className="bg-orange-600 text-white px-3 py-2 rounded-t-md -mx-4 -mt-4">
              <div className="flex items-center justify-between">
                <div>Call #{id ? id.toString().slice(0,8) : '—'}</div>
                <div className="text-xs bg-black/10 px-2 py-0.5 rounded">DISPATCH</div>
              </div>
            </div>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-24" />
              ) : (
                <>
                  <div className="text-lg font-semibold">{call?.caller_name || 'Unknown'}</div>
                  <div className="text-2xl text-orange-600 font-bold">{call?.phone || '—'}</div>
                  <div className="text-sm text-gray-500">Received: {formatters.formatDate(call?.received_at)}</div>
                  <div className="mt-2"><Badge>{call?.language || 'Unknown'}</Badge> <Badge>{call?.status || 'Unknown'}</Badge></div>
                  <div className="text-sm mt-2">Duration: {formatters.formatDuration(call?.duration || 0)}</div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Emergency Signals Queue</CardTitle>
            </CardHeader>
            <CardContent>
              {lastFive.isLoading ? (
                <div>{new Array(5).fill(0).map((_,i)=>(<Skeleton key={i} className="h-6 mb-2"/>))}</div>
              ) : (
                <div className="text-sm">
                  <div className="grid grid-cols-5 font-medium mb-2"> <div>#</div><div>Type</div><div>Number</div><div>Time</div><div>Status</div></div>
                  {lastFive.data && Array.isArray(lastFive.data) && lastFive.data.map((c, idx) => (
                    <div key={c.id} className={`grid grid-cols-5 items-center py-1 ${c.id === call?.id ? 'bg-gray-100' : ''}`}>
                      <div>{idx+1}</div>
                      <div className="text-xs">{c.category}</div>
                      <div className="text-xs">{c.phone}</div>
                      <div className="text-xs">{formatters.formatDate(c.received_at)}</div>
                      <div className="text-xs">{c.status}</div>
                    </div>
                  ))}
                  <div className="mt-2 text-right"><a className="text-sm text-blue-600" href="#" onClick={(e)=>{e.preventDefault(); navigate('/calls')}}>View All Calls</a></div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>AI Pipeline Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {pipelineSteps.map((s) => (
                  <div key={s.key} className="flex items-center justify-between">
                    <div className="text-sm">{s.label}</div>
                    <div className="text-sm text-gray-600">{s.state === 'Completed' ? '✔' : s.state === 'InProgress' ? '⏳' : '○'}</div>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex space-x-2">
                <Button onClick={() => runPipelineMutation.mutate(id)}>Re-run Pipeline</Button>
                <Button variant="secondary" onClick={() => { refetch(); refetchPipeline(); }}>Refresh</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Audio</CardTitle></CardHeader>
            <CardContent>
              {isLoading ? <Skeleton className="h-12" /> : (
                call?.audio_url ? (
                  <audio controls src={call.audio_url} className="w-full" />
                ) : (
                  <div>
                    <div>No audio file available</div>
                    <div className="mt-2 flex space-x-2">
                      <Button onClick={() => setShowUpload(s => !s)}>Upload Audio</Button>
                      <Button variant="secondary" onClick={() => runPipelineMutation.mutate(id)}>Start Pipeline</Button>
                    </div>
                    {showUpload && <div className="mt-3"><FileUploadDropzone callId={id} onComplete={() => { refetch(); setShowUpload(false); }} /></div>}
                  </div>
                )
              )}
            </CardContent>
          </Card>

          <div className="mt-4">
            <PipelineProgressTracker callId={id} />
          </div>
        </div>

        {/* CENTER COLUMN */}
        <div>
          <Card>
            <CardContent>
              {isLoading ? <Skeleton className="h-24" /> : (
                <>
                  <div className="text-sm text-gray-500">Caller Details</div>
                  <div className="text-3xl font-bold text-orange-600">{call?.phone || '—'}</div>
                  <div className="text-xl">{call?.caller_name || 'Unknown'}</div>
                  <div className="mt-2 text-sm text-gray-600">{call?.address || 'Address not available'}</div>
                  <div className="mt-2"><Button onClick={()=>window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(call?.address || '')}`, '_blank')}>Get Location</Button></div>
                </>
              )}
            </CardContent>
          </Card>

          <div className="mt-4">
            <Tabs defaultValue="transcript">
              <TabsList>
                <TabsTrigger value="transcript">Transcript</TabsTrigger>
                <TabsTrigger value="classification">Classification</TabsTrigger>
                <TabsTrigger value="audio_events">Audio Events</TabsTrigger>
              </TabsList>
              <div className="mt-3">
                <TabsContent value="transcript">
                  {isLoading ? <Skeleton className="h-40" /> : (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="font-medium">Raw</div>
                        <div className="mt-2 whitespace-pre-wrap">{call?.transcript_raw || '—'}</div>
                      </div>
                      <div>
                        <div className="font-medium">Cleaned</div>
                        <div className="mt-2 whitespace-pre-wrap">{call?.transcript_cleaned || '—'}</div>
                        <div className="mt-3">
                          <div className="font-medium">Keywords</div>
                          <div className="mt-2">{(call?.keywords || []).map(k=>(<span key={k} className="inline-block bg-gray-100 px-2 py-1 mr-1 rounded text-xs">{k}</span>))}</div>
                        </div>
                        <div className="mt-3 text-sm text-gray-500">Language: {call?.language || '—'} • Processing Time: {call?.processing_time ? `${call.processing_time}s` : '—'}</div>
                      </div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="classification">
                  {isLoading ? <Skeleton className="h-40" /> : (
                    <div>
                      <div className="text-lg font-medium">Category: {call?.category || '—'}</div>
                      <div className="text-sm">Confidence: {call?.classification_confidence ? `${(call.classification_confidence*100).toFixed(1)}%` : '—'}</div>
                      <div className="mt-3">Model: {call?.model_name || '—'}</div>
                      <div className="mt-4">
                        <div className="font-medium">History</div>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Time</TableHead>
                              <TableHead>Category</TableHead>
                              <TableHead>Confidence</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(call?.classification_history || []).map((h) => (
                              <TableRow key={h.time}>
                                <TableCell>{formatters.formatDate(h.time)}</TableCell>
                                <TableCell>{h.category}</TableCell>
                                <TableCell>{h.confidence}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="audio_events">
                  {isLoading ? <Skeleton className="h-40" /> : (
                    <div>
                      {(call?.audio_events || []).length === 0 ? <div>No audio events found</div> : (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Event</TableHead>
                              <TableHead>Confidence</TableHead>
                              <TableHead>Start</TableHead>
                              <TableHead>End</TableHead>
                              <TableHead>Progress</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(call?.audio_events || []).map((e, i) => (
                              <TableRow key={i}>
                                <TableCell>{e.event}</TableCell>
                                <TableCell>{e.confidence}</TableCell>
                                <TableCell>{e.start}</TableCell>
                                <TableCell>{e.end}</TableCell>
                                <TableCell><div className="w-24 h-2 bg-gray-200"><div style={{ width: `${(e.confidence||0)*100}%` }} className="h-2 bg-green-500" /></div></TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      )}
                    </div>
                  )}
                </TabsContent>
              </div>
            </Tabs>
          </div>

          <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2">
            <div className="flex space-x-2">
              <Button onClick={()=>window.alert('Calling...')} className="bg-orange-600 text-white">Call</Button>
              <Button onClick={()=>window.alert('Report generated')}>Generate Report</Button>
              <Button onClick={()=>{ const audioEl = document.querySelector('audio'); if (audioEl) audioEl.play(); }}>Play Audio</Button>
              <Button onClick={()=>window.alert('Add services')}>Add Services</Button>
              <Button variant="ghost" onClick={()=>navigate('/calls')}>Close</Button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Severity</CardTitle></CardHeader>
            <CardContent>
              {isLoading ? <Skeleton className="h-24" /> : (
                <div className="text-center">
                  <div className="text-sm">Priority</div>
                  <div className="text-2xl font-bold">{call?.priority || '—'}</div>
                  <div className="text-4xl font-extrabold mt-2">{formatters.formatScore(call?.score || 0)} / 100</div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Score Breakdown</CardTitle></CardHeader>
            <CardContent>
              {isLoading ? <Skeleton className="h-32" /> : (
                call?.score_breakdown == null ? (
                  <div className="text-sm text-gray-600">Score breakdown not yet available</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Component</TableHead>
                        <TableHead>Score</TableHead>
                        <TableHead>Weight</TableHead>
                        <TableHead>Contribution</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(call?.score_breakdown || []).map((s, i) => (
                        <TableRow key={i}>
                          <TableCell>{s.component}</TableCell>
                          <TableCell>{s.score}</TableCell>
                          <TableCell>{s.weight}</TableCell>
                          <TableCell>{s.contribution}</TableCell>
                        </TableRow>
                      ))}
                      <TableRow>
                        <TableCell>Total</TableCell>
                        <TableCell>{call?.score_total || '—'}</TableCell>
                        <TableCell>-</TableCell>
                        <TableCell>{call?.score_total || '—'}</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                )
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>SOP Recommendations</CardTitle></CardHeader>
            <CardContent>
              {isLoading ? <Skeleton className="h-24" /> : (
                <div>
                  {(SOP_ACTIONS[call?.category] || []).map((act, idx) => (
                    <div key={idx} className="flex items-start space-x-2">
                      <input type="checkbox" className="mt-1" />
                      <div className="text-sm">{act}</div>
                    </div>
                  ))}
                  <div className="mt-2">
                    <Textarea value={sopComments} onChange={(e)=>setSopComments(e.target.value)} placeholder="Comments" />
                    <div className="flex space-x-2 mt-2">
                      <Button onClick={()=>window.alert('Edit SOP')}>Edit</Button>
                      <Button onClick={()=>window.alert('Associate signal')}>Associated Signal</Button>
                      <Button onClick={()=>window.alert('Transfer case')}>Transfer Case</Button>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Dispatch Panel</CardTitle></CardHeader>
            <CardContent>
              <div className="mb-2">
                <label className="block text-sm">Department</label>
                <select value={dispatchDept} onChange={(e)=>setDispatchDept(e.target.value)} className="w-full p-2 border rounded">
                  {DEPARTMENTS.map((d)=> <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div className="mb-2">
                <label className="block text-sm">Officer</label>
                <input value={officer} onChange={(e)=>setOfficer(e.target.value)} className="w-full p-2 border rounded" />
              </div>
              <div className="flex space-x-2">
                <Button onClick={onDispatch}>Dispatch</Button>
                <Button variant="secondary" onClick={()=>window.alert('Show existing dispatches')}>Existing</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Incident</CardTitle></CardHeader>
            <CardContent>
              {call?.incident ? (
                <div>
                  <div className="font-medium">{call.incident.title}</div>
                  <div>Severity: {call.incident.severity}</div>
                  <div>Calls: {call.incident.call_count}</div>
                  <div className="mt-2"><Button onClick={()=>navigate(`/incidents/${call.incident.id}`)}>View Incident</Button></div>
                </div>
              ) : (
                <div>
                  <div>Not Yet Correlated</div>
                  <div className="mt-2"><Button onClick={()=>window.alert('Run Correlation')}>Run Correlation</Button></div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
