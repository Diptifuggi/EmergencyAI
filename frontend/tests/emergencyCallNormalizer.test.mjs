import test from 'node:test'
import assert from 'node:assert/strict'
import {
  buildCallMetrics,
  buildDailyCallSeries,
  normalizeCallCollection,
  normalizeEmergencyCall,
  safeChartData,
} from '../src/lib/emergencyCallNormalizer.js'

const fireCall = {
  id: 'fire-1',
  status: 'analyzed',
  priority: 'critical',
  call_type: 'text',
  text_content: 'A building is on fire.',
  language: 'en-IN',
  created_at: '2026-10-27T09:00:00+05:30',
  latitude: '22.5399058',
  longitude: '72.9274484',
  location_accuracy: 14.557,
  location_address: null,
  location_status: 'captured',
  map_snapshot_available: true,
  map_snapshot_url: '/api/v1/emergency-calls/fire-1/map-snapshot',
  client_metadata: {
    emergency_analysis: {
      emergency_type: 'fire',
      severity: 'CRITICAL',
      priority_level: 'CRITICAL',
      priority_score: 100,
      victim_count: 10,
      fire_present: true,
      smoke_present: true,
      help_required: ['fire_service'],
      recommended_units: ['fire_service'],
      dispatch_recommendation: {
        recommended_units: ['fire_service'],
        emergency_numbers: { '101': 'Fire Service' },
        reason: 'Active building fire.',
        priority_reason: 'People reported at risk.',
        dispatcher_action: 'Confirm location and response.',
      },
    },
  },
}

test('normalizes the nested fire analysis, coordinates, contacts and map snapshot', () => {
  const call = normalizeEmergencyCall(fireCall)
  assert.equal(call.category, 'fire')
  assert.equal(call.priority, 'Critical')
  assert.equal(call.priorityScore, 100)
  assert.equal(call.analysis.victim_count, 10)
  assert.equal(call.indicators.fire_present, true)
  assert.deepEqual(call.helpRequired, ['fire_service'])
  assert.deepEqual(call.recommendedUnits, ['fire_service'])
  assert.equal(call.latitude, 22.5399058)
  assert.equal(call.longitude, 72.9274484)
  assert.equal(call.locationAccuracy, 14.557)
  assert.equal(call.locationAddress, null)
  assert.equal(call.locationAddressStatus, 'unavailable')
  assert.equal(call.mapSnapshotAvailable, true)
  assert.equal(call.mapSnapshotUrl, '/api/v1/emergency-calls/fire-1/map-snapshot')
  assert.equal(call.callerName, null)
})

test('preserves pending and resolved address lifecycle independently from GPS capture', () => {
  const pending = normalizeEmergencyCall({
    latitude: 12.5,
    longitude: -45.6,
    location_status: 'captured',
    location_address_status: 'pending',
  })
  const resolved = normalizeEmergencyCall({
    latitude: 12.5,
    longitude: -45.6,
    location_status: 'captured',
    location_address: 'Example locality',
    location_address_status: 'resolved',
  })

  assert.equal(pending.locationStatus, 'captured')
  assert.equal(pending.locationAddressStatus, 'pending')
  assert.equal(resolved.locationStatus, 'captured')
  assert.equal(resolved.locationAddressStatus, 'resolved')
  assert.equal(resolved.locationAddress, 'Example locality')
})

test('supports wrapped item collections and deduplicates records by id', () => {
  const calls = normalizeCallCollection({ data: { items: [fireCall, fireCall], total: 2 } })
  assert.equal(calls.length, 1)
  assert.equal(calls[0].id, 'fire-1')
})

test('normalizes medical and road-accident categories without treating call type as category', () => {
  const medical = normalizeEmergencyCall({
    client_metadata: { emergency_analysis: { emergency_type: 'medical', help_required: ['ambulance'] } },
    priority: 'HIGH',
  })
  const accident = normalizeEmergencyCall({
    client_metadata: { emergency_analysis: { emergency_type: 'road_accident' } },
  })
  const missing = normalizeEmergencyCall({ call_type: 'text', status: 'analysis_failed' })
  assert.equal(medical.category, 'medical')
  assert.equal(medical.priority, 'High')
  assert.equal(accident.category, 'road_accident')
  assert.equal(missing.category, null)
  assert.deepEqual(missing.helpRequired, [])
  assert.equal(missing.priority, null)
  assert.equal(missing.status, 'analysis_failed')
})

test('validates coordinates, preserves zero scores, and falls back to valid nested coordinates', () => {
  const call = normalizeEmergencyCall({
    latitude: 91,
    longitude: 'not-a-coordinate',
    priority_score: 0,
    location: { latitude: '0', longitude: '0' },
    client_metadata: { emergency_analysis: { priority_score: 0, confidence: 0 } },
  })
  assert.equal(call.latitude, 0)
  assert.equal(call.longitude, 0)
  assert.equal(call.priorityScore, 0)
  assert.equal(call.confidence, 0)
})

test('uses complete coordinate pairs, reports conflicts, and preserves capture time', () => {
  const conflicting = normalizeEmergencyCall({
    latitude: 0,
    longitude: 0,
    location_timestamp: '2026-10-27T10:00:00Z',
    location: { latitude: 10, longitude: 20 },
  })
  const partialTopLevel = normalizeEmergencyCall({
    latitude: 91,
    longitude: null,
    location: { latitude: 22.5, longitude: 72.9 },
  })
  const invalid = normalizeEmergencyCall({ latitude: 'bad', longitude: 200 })

  assert.equal(conflicting.latitude, 0)
  assert.equal(conflicting.longitude, 0)
  assert.equal(conflicting.locationCoordinatesConflict, true)
  assert.equal(conflicting.locationTimestamp, '2026-10-27T10:00:00Z')
  assert.equal(partialTopLevel.latitude, 22.5)
  assert.equal(partialTopLevel.longitude, 72.9)
  assert.equal(partialTopLevel.locationCoordinatesStatus, 'valid')
  assert.equal(invalid.locationCoordinatesStatus, 'invalid')
  assert.equal(normalizeEmergencyCall({}).locationCoordinatesStatus, 'missing')
})

test('groups local-day call volume, includes zero days, and does not lose zero score', () => {
  const now = new Date(2026, 9, 27, 12)
  const calls = normalizeCallCollection([
    { ...fireCall, id: 'a', created_at: '2026-10-27T08:00:00' },
    { ...fireCall, id: 'b', created_at: '2026-10-25T08:00:00', client_metadata: { emergency_analysis: { emergency_type: 'medical', priority_score: 0 } } },
  ])
  const series = buildDailyCallSeries(calls, 7, now)
  const metrics = buildCallMetrics(calls, now)
  assert.equal(series.labels.length, 7)
  assert.equal(series.data.length, 7)
  assert.equal(series.data.reduce((sum, count) => sum + count, 0), 2)
  assert.equal(metrics.totalCalls, 2)
  assert.equal(metrics.averagePriorityScore, 50)
  assert.equal(metrics.dispatched, null)
  assert.equal(metrics.activeIncidents, null)
  const recordedDispatch = normalizeEmergencyCall({
    ...fireCall,
    client_metadata: { ...fireCall.client_metadata, dispatches: [{ details: { unit: 'fire_service' } }] },
  })
  assert.equal(buildCallMetrics([recordedDispatch], now).dispatched, 1)
})

test('empty and malformed chart inputs always produce valid aligned Chart.js arrays', () => {
  assert.deepEqual(safeChartData(undefined, undefined), {
    labels: [],
    datasets: [{ label: 'Calls', data: [] }],
  })
  const malformed = safeChartData(
    ['Fire', null, 'Medical', 'Extra'],
    [2, 8, 'bad'],
    { backgroundColor: ['#111', '#222', '#333'] },
  )
  assert.deepEqual(malformed.labels, ['Fire'])
  assert.deepEqual(malformed.datasets[0].data, [2])
  assert.deepEqual(malformed.datasets[0].backgroundColor, ['#111'])
  assert.deepEqual(normalizeCallCollection({ items: null }), [])
  assert.deepEqual(buildCallMetrics([]).categories, [])
})
