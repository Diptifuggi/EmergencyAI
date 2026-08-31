export const severityColor = (s) => {
  if (s === 'critical') return 'text-red-600'
  if (s === 'high') return 'text-orange-600'
  return 'text-green-600'
}
