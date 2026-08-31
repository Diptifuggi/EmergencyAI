// @ts-nocheck
export interface Incident {
  id: string
  title: string
  description?: string
  location?: {
    lat: number
    lng: number
  }
  severity?: number
}
