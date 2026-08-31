// @ts-nocheck
export interface EmergencyCall {
  id: string
  caller: string
  timestamp: string
  location?: {
    lat: number
    lng: number
    address?: string
  }
  severity?: number
}
