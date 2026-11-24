const isRecord = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)

const nonEmptyString = (...values) => {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return null
}

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

const coordinate = (values, minimum, maximum) => {
  for (const value of values) {
    const parsed = finiteNumber(value)
    if (parsed !== null && parsed >= minimum && parsed <= maximum) return parsed
  }
  return null
}

const analysisForRawCall = (call) => {
  const metadata = isRecord(call.client_metadata) ? call.client_metadata : {}
  let analysis = metadata.emergency_analysis ?? metadata.analysis ?? call.emergency_analysis ?? call.analysis
  if (!isRecord(analysis)) return {}
  if (isRecord(analysis.analysis)) analysis = analysis.analysis
  return isRecord(analysis) ? analysis : {}
}

export const normalizePriority = (...values) => {
  const raw = nonEmptyString(...values)
  if (!raw) return null
  const key = raw.toLowerCase().replace(/[\s-]+/g, '_')
  if (key === 'normal') return null
  const labels = {
    critical: 'Critical',
    very_high: 'Very High',
    high: 'High',
    moderate: 'Moderate',
    medium: 'Moderate',
    low: 'Low',
  }
  return labels[key] ?? raw.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export const normalizeEmergencyCall = (response) => {
  let raw = response
  if (isRecord(raw?.data)) raw = raw.data
  if (isRecord(raw?.call)) raw = raw.call
  if (!isRecord(raw)) raw = {}

  const metadata = isRecord(raw.client_metadata) ? raw.client_metadata : {}
  const analysis = analysisForRawCall(raw)
  const dispatchRecords = Array.isArray(raw.dispatches)
    ? raw.dispatches
    : Array.isArray(metadata.dispatches)
      ? metadata.dispatches
      : []
  const location = isRecord(raw.location) ? raw.location : {}
  const topLevelCoordinates = {
    latitude: coordinate([raw.latitude], -90, 90),
    longitude: coordinate([raw.longitude], -180, 180),
  }
  const nestedCoordinates = {
    latitude: coordinate([location.latitude, location.lat], -90, 90),
    longitude: coordinate([location.longitude, location.lng], -180, 180),
  }
  const hasTopLevelPair = topLevelCoordinates.latitude !== null && topLevelCoordinates.longitude !== null
  const hasNestedPair = nestedCoordinates.latitude !== null && nestedCoordinates.longitude !== null
  // Dedicated top-level API columns are canonical; nested coordinates are a fallback pair.
  const selectedCoordinates = hasTopLevelPair ? topLevelCoordinates : nestedCoordinates
  const hasAnyCoordinateInput = [
    raw.latitude,
    raw.longitude,
    location.latitude,
    location.longitude,
    location.lat,
    location.lng,
  ].some((value) => value !== null && value !== undefined && value !== '')
  const coordinatesConflict = hasTopLevelPair && hasNestedPair && (
    topLevelCoordinates.latitude !== nestedCoordinates.latitude
    || topLevelCoordinates.longitude !== nestedCoordinates.longitude
  )
  const recommendation = isRecord(analysis.dispatch_recommendation)
    ? analysis.dispatch_recommendation
    : {}
  const helpRequired = Array.isArray(analysis.help_required) ? analysis.help_required : []
  const units = Array.isArray(analysis.recommended_units)
    ? analysis.recommended_units
    : Array.isArray(recommendation.recommended_units)
      ? recommendation.recommended_units
      : []
  const accuracyCandidates = [raw.location_accuracy, location.accuracy_meters, location.accuracy]
    .map(finiteNumber)
  const accuracy = accuracyCandidates.find((value) => value !== null && value >= 0) ?? null
  const originalText = nonEmptyString(raw.text_content, raw.transcription)
  const cleanTranscript = nonEmptyString(raw.transcription)

  return {
    ...raw,
    raw,
    id: raw.id == null ? null : String(raw.id),
    analysis,
    textContent: nonEmptyString(raw.text_content),
    transcription: nonEmptyString(raw.transcription),
    originalTranscript: originalText,
    cleanTranscript,
    language: nonEmptyString(raw.language, raw.requested_language, metadata.requested_language),
    requestedLanguage: nonEmptyString(raw.requested_language, metadata.requested_language),
    status: nonEmptyString(raw.status),
    category: nonEmptyString(analysis.emergency_type, raw.emergency_type),
    subType: nonEmptyString(analysis.sub_type),
    priority: normalizePriority(analysis.priority_level, raw.priority),
    severity: analysis.severity ?? null,
    priorityScore: finiteNumber(analysis.priority_score ?? raw.priority_score ?? raw.final_score),
    confidence: finiteNumber(analysis.confidence),
    emergencyKeywords: Array.isArray(analysis.emergency_keywords) ? analysis.emergency_keywords : [],
    helpRequired,
    recommendedUnits: units,
    dispatchRecommendation: recommendation,
    dispatchRecords,
    indicators: Object.fromEntries([
      'victim_count', 'injuries_present', 'unconscious_person', 'severe_bleeding',
      'medical_emergency', 'immediate_danger', 'fire_present', 'explosion_present',
      'trapped_persons', 'rescue_required', 'railway_incident', 'road_accident',
      'highway_incident', 'weapon_present', 'child_involved', 'elderly_involved',
      'domestic_violence', 'crime_in_progress', 'police_required', 'sexual_violence',
      'missing_person', 'burglary_in_progress', 'home_intrusion', 'robbery_in_progress',
      'assault_in_progress', 'smoke_present', 'children_involved', 'cyber_crime', 'lpg_leak',
      'heavy_rain', 'flood_risk', 'flood_confirmed',
    ].filter((key) => Object.prototype.hasOwnProperty.call(analysis, key))
      .map((key) => [key, analysis[key]])),
    latitude: selectedCoordinates.latitude,
    longitude: selectedCoordinates.longitude,
    locationCoordinatesStatus: hasTopLevelPair || hasNestedPair
      ? 'valid'
      : hasAnyCoordinateInput
        ? 'invalid'
        : 'missing',
    locationCoordinatesConflict: coordinatesConflict,
    locationAccuracy: accuracy,
    locationTimestamp: nonEmptyString(raw.location_timestamp, location.captured_at),
    locationStatus: nonEmptyString(raw.location_status, location.status),
    locationAddress: nonEmptyString(raw.location_address, location.address),
    locationAddressStatus: nonEmptyString(raw.location_address_status, location.address_status)
      || (nonEmptyString(raw.location_address, location.address) ? 'unknown' : 'unavailable'),
    mapSnapshotAvailable: raw.map_snapshot_available === true,
    mapSnapshotUrl: nonEmptyString(raw.map_snapshot_url),
    createdAt: nonEmptyString(raw.created_at),
    source: nonEmptyString(raw.source, metadata.source),
    platform: nonEmptyString(metadata.platform, raw.platform),
    callerName: nonEmptyString(raw.caller_name, metadata.caller_name),
    callerPhone: nonEmptyString(raw.caller_phone, metadata.caller_phone),
    callerEmail: nonEmptyString(raw.caller_email, metadata.caller_email),
  }
}

export const callItemsFromResponse = (response) => {
  let value = response
  for (let depth = 0; depth < 4 && isRecord(value); depth += 1) {
    if (Array.isArray(value.items)) return value.items
    if (Array.isArray(value.calls)) return value.calls
    if (Array.isArray(value.results)) return value.results
    value = value.data
  }
  return Array.isArray(value) ? value : []
}

export const normalizeCallCollection = (response) => {
  const unique = new Map()
  callItemsFromResponse(response).forEach((item, index) => {
    const call = normalizeEmergencyCall(item)
    const key = call.id ?? `unidentified-${index}`
    if (!unique.has(key)) unique.set(key, call)
  })
  return [...unique.values()]
}

export const localDateKey = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export const buildDailyCallSeries = (calls, days, now = new Date()) => {
  const counts = new Map()
  const dates = []
  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - offset)
    const key = localDateKey(date)
    dates.push({ date, key })
    counts.set(key, 0)
  }
  for (const call of calls) {
    const timestamp = call.createdAt ? new Date(call.createdAt) : null
    if (!timestamp || Number.isNaN(timestamp.getTime())) continue
    const key = localDateKey(timestamp)
    if (counts.has(key)) counts.set(key, counts.get(key) + 1)
  }
  return {
    labels: dates.map(({ date }) => date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })),
    data: dates.map(({ key }) => counts.get(key)),
  }
}

export const safeChartData = (labels, values, dataset = {}) => {
  const sourceLabels = Array.isArray(labels) ? labels : []
  const sourceValues = Array.isArray(values) ? values : []
  const length = Math.min(sourceLabels.length, sourceValues.length)
  const validLabels = []
  const validValues = []
  const validColors = []

  for (let index = 0; index < length; index += 1) {
    const label = sourceLabels[index]
    const rawValue = sourceValues[index]
    if (label === null || label === undefined || rawValue === null || rawValue === undefined || rawValue === '') continue
    const value = Number(rawValue)
    if (!Number.isFinite(value)) continue
    validLabels.push(String(label))
    validValues.push(value)
    if (Array.isArray(dataset.backgroundColor) && dataset.backgroundColor.length > 0) {
      validColors.push(dataset.backgroundColor[index % dataset.backgroundColor.length])
    }
  }

  return {
    labels: validLabels,
    datasets: [{
      label: 'Calls',
      ...dataset,
      ...(Array.isArray(dataset.backgroundColor) ? { backgroundColor: validColors } : {}),
      data: validValues,
    }],
  }
}

export const buildCallMetrics = (calls, now = new Date()) => {
  const categories = new Map()
  const priorities = new Map([['Critical', 0], ['Very High', 0], ['High', 0], ['Moderate', 0], ['Low', 0]])
  const statuses = new Map()
  const channels = new Map()
  const scores = []
  let resolved = 0
  let pending = 0
  let today = 0
  let dispatched = 0
  let dispatchEvidenceCount = 0

  for (const call of calls) {
    const category = call.category ?? 'Not reported'
    categories.set(category, (categories.get(category) ?? 0) + 1)
    if (call.priority) priorities.set(call.priority, (priorities.get(call.priority) ?? 0) + 1)
    const statusKey = (call.status ?? 'Not reported').toLowerCase().replaceAll('_', ' ')
    const statusLabel = statusKey.replace(/\b\w/g, (letter) => letter.toUpperCase())
    statuses.set(statusLabel, (statuses.get(statusLabel) ?? 0) + 1)
    const channel = call.source ?? call.platform ?? 'Not reported'
    channels.set(channel, (channels.get(channel) ?? 0) + 1)

    if (call.priorityScore !== null) scores.push(call.priorityScore)
    if (['resolved', 'closed'].includes(statusKey)) resolved += 1
    if (['received', 'pending transcription', 'analyzing'].includes(statusKey)) pending += 1
    if (statusKey === 'dispatched') {
      dispatched += 1
      dispatchEvidenceCount += 1
    } else if (call.dispatchRecords.length > 0) {
      const confirmedDispatches = call.dispatchRecords.filter((item) =>
        isRecord(item?.details) ||
        ['dispatched', 'en route', 'en_route', 'completed'].includes(String(item?.status ?? '').toLowerCase())
      )
      dispatched += confirmedDispatches.length
      dispatchEvidenceCount += confirmedDispatches.length
    }
    const created = call.createdAt ? new Date(call.createdAt) : null
    if (created && !Number.isNaN(created.getTime()) && localDateKey(created) === localDateKey(now)) today += 1
  }

  const criticalCalls = calls
    .filter((call) => call.priority === 'Critical')
    .sort((left, right) => new Date(right.createdAt ?? 0).getTime() - new Date(left.createdAt ?? 0).getTime())
    .slice(0, 5)

  return {
    totalCalls: calls.length,
    criticalCalls: priorities.get('Critical') ?? 0,
    todaysCalls: today,
    resolved,
    dispatched: dispatchEvidenceCount > 0 ? dispatched : null,
    averagePriorityScore: scores.length ? scores.reduce((sum, score) => sum + score, 0) / scores.length : null,
    pending,
    activeIncidents: null,
    categories: [...categories.entries()].sort(([left], [right]) => left.localeCompare(right)),
    priorities: [...priorities.entries()].map(([level, count]) => ({ level, count })),
    statuses: [...statuses.entries()],
    channels: [...channels.entries()].map(([source, count]) => ({ source, count })),
    recentCriticalCalls: criticalCalls,
    callRate7Days: buildDailyCallSeries(calls, 7, now),
  }
}

export const normalizeIncidentRecord = (incident) => {
  const raw = isRecord(incident) ? incident : {}
  const coordinates = normalizeEmergencyCall({
    ...raw,
    emergency_type: raw.incident_type,
    latitude: raw.latitude,
    longitude: raw.longitude,
  })
  const severity = finiteNumber(raw.severity)
  return {
    ...coordinates,
    title: nonEmptyString(raw.title),
    description: nonEmptyString(raw.description),
    category: nonEmptyString(raw.incident_type),
    priority: normalizePriority(raw.priority),
    severityScore: severity,
    severityLabel: typeof raw.severity === 'string' ? raw.severity : null,
    incidentStatus: nonEmptyString(raw.status),
    callCount: finiteNumber(raw.call_count),
  }
}
