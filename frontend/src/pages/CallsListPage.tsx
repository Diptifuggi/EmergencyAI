// @ts-nocheck
import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { DebounceInput } from 'react-debounce-input'

import callsApi from '@/api/callsApi'
import { API_BASE_URL, CALL_STATUSES, CATEGORIES, PRIORITY_CONFIG } from '@/lib/constants'
import formatters from '@/lib/formatters'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Button,
  Skeleton,
  Input,
  Select,
} from '@/components/ui'

export default function CallsListPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [localSearch, setLocalSearch] = useState(searchParams.get('q') || '')
  const [page, setPage] = useState(Number(searchParams.get('page') || 1))
  const [pageSize, setPageSize] = useState(Number(searchParams.get('page_size') || 20))

  useEffect(() => {
    setLocalSearch(searchParams.get('q') || '')
    setPage(Number(searchParams.get('page') || 1))
    setPageSize(Number(searchParams.get('page_size') || 20))
  }, [searchParams])

  // Build params from URL search params
  const params = useMemo(() => {
    const p = {}
    const q = searchParams.get('q')
    if (q) p.q = q
    const status = searchParams.get('status')
    if (status) p.status = status
    const category = searchParams.get('category')
    if (category) p.category = category
    const priority = searchParams.get('priority')
    if (priority) p.priority = priority
    const from = searchParams.get('from')
    if (from) p.from = from
    const to = searchParams.get('to')
    if (to) p.to = to
    p.page = searchParams.get('page') || 1
    p.page_size = searchParams.get('page_size') || pageSize
    return p
  }, [searchParams, pageSize])

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['calls', params],
    queryFn: () => callsApi.listCalls(params),
    refetchInterval: 15000,
  })

  const items = Array.isArray(data) ? data : (data?.items || data?.results || [])
  const total = data?.total ?? (Array.isArray(data) ? items.length : items.length)

  function applyFilters() {
    const sp = new URLSearchParams()
    if (localSearch) sp.set('q', localSearch)
    const status = document.getElementById('filter-status')?.value
    if (status) sp.set('status', status)
    const category = document.getElementById('filter-category')?.value
    if (category) sp.set('category', category)
    const priority = document.getElementById('filter-priority')?.value
    if (priority) sp.set('priority', priority)
    const from = document.getElementById('filter-from')?.value
    if (from) sp.set('from', from)
    const to = document.getElementById('filter-to')?.value
    if (to) sp.set('to', to)
    sp.set('page', '1')
    sp.set('page_size', String(pageSize))
    setSearchParams(sp)
  }

  function clearAll() {
    setLocalSearch('')
    setSearchParams({ page: '1', page_size: String(pageSize) })
  }

  function onPageChange(next) {
    const sp = new URLSearchParams(searchParams.toString())
    sp.set('page', String(next))
    setSearchParams(sp)
  }

  async function onRunPipeline(id) {
    try {
      await callsApi.runPipeline(id)
      refetch()
    } catch (e) {
      console.error(e)
    }
  }

  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  return (
    <div className="flex min-h-screen">
      <aside className="w-72 sticky top-0 p-4">
        <Card>
          <CardHeader>
            <CardTitle>Filter Calls</CardTitle>
          </CardHeader>
          <CardContent>
            <label className="block text-sm font-medium mb-1">Search</label>
            <DebounceInput element={Input} minLength={1} debounceTimeout={400} value={localSearch} onChange={(e) => setLocalSearch(e.target.value)} className="mb-2 w-full" />

            <label className="block text-sm font-medium mb-1">Status</label>
            <select id="filter-status" defaultValue={searchParams.get('status') || ''} className="mb-2 w-full p-2 border rounded">
              <option value="">Any</option>
              {CALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>

            <label className="block text-sm font-medium mb-1">Category</label>
            <select id="filter-category" defaultValue={searchParams.get('category') || ''} className="mb-2 w-full p-2 border rounded">
              <option value="">Any</option>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>

            <label className="block text-sm font-medium mb-1">Priority</label>
            <select id="filter-priority" defaultValue={searchParams.get('priority') || ''} className="mb-2 w-full p-2 border rounded">
              <option value="">Any</option>
              {Object.keys(PRIORITY_CONFIG).map((p) => <option key={p} value={p}>{p}</option>)}
            </select>

            <label className="block text-sm font-medium mb-1">Date From</label>
            <input id="filter-from" type="date" defaultValue={searchParams.get('from') || ''} className="mb-2 w-full p-2 border rounded" />

            <label className="block text-sm font-medium mb-1">Date To</label>
            <input id="filter-to" type="date" defaultValue={searchParams.get('to') || ''} className="mb-4 w-full p-2 border rounded" />

            <div className="flex space-x-2">
              <Button onClick={applyFilters}>Apply Filters</Button>
              <Button variant="secondary" onClick={clearAll}>Clear All</Button>
            </div>
          </CardContent>
        </Card>
      </aside>

      <main className="flex-1 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-semibold">Live Calls</h1>
            <div className="text-sm text-gray-500">Auto-refreshing every 15s • <span className="inline-block w-2 h-2 bg-green-500 rounded-full align-middle mr-1" /></div>
          </div>
          <div className="flex items-center space-x-2">
            <div className="text-sm text-gray-700">{total} total</div>
          </div>
        </div>

        <Card>
          <CardContent>
            {isLoading ? (
              <div>
                {new Array(10).fill(0).map((_, i) => (
                  <div key={i} className="py-3"><Skeleton className="h-6 w-full" /></div>
                ))}
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Caller</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Received</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((c) => (
                      <TableRow key={c.id} className={`${c.priority === 'Critical' ? 'border-l-4 border-l-red-600' : c.priority === 'Very High' ? 'border-l-4 border-l-orange-500' : c.priority === 'High' ? 'border-l-4 border-l-amber-500' : ''}`}>
                        <TableCell>{c.caller_name}</TableCell>
                        <TableCell>{c.phone}</TableCell>
                        <TableCell>{formatters.formatDate(c.received_at)}</TableCell>
                        <TableCell>{c.category}</TableCell>
                        <TableCell>{c.priority}</TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <div className="text-sm">{formatters.formatScore(c.score || 0)} / 100</div>
                            <div style={{ width: 40 }} className="h-1 bg-gray-200 rounded">
                              <div className="h-1 rounded" style={{ width: `${Math.min(100, c.score || 0)}%`, background: formatters.getScoreColor(c.score || 0) }} />
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>{c.status}</TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <Button size="sm" onClick={() => navigate(`/calls/${c.id}`)}>View</Button>
                            <Button size="sm" title="Re-run AI pipeline" onClick={() => onRunPipeline(c.id)}>Re-run</Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
                  <div>Showing {start}-{end} of {total} calls</div>
                  <div className="flex items-center space-x-2">
                    <Button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Prev</Button>
                    <div>Page {page}</div>
                    <Button disabled={end >= total} onClick={() => onPageChange(page + 1)}>Next</Button>
                    <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); const sp = new URLSearchParams(searchParams.toString()); sp.set('page_size', e.target.value); sp.set('page', '1'); setSearchParams(sp); }} className="p-1 border rounded">
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
