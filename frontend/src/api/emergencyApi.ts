// @ts-nocheck
import { listCalls, getCall } from './callsApi'

export async function getEmergencies(params: Record<string, any> = {}) {
  // backward-compat: delegate to callsApi
  return listCalls(params)
}

export async function getEmergency(id: string) {
  return getCall(id)
}
