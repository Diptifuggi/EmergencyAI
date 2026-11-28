// @ts-nocheck
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { tokenStore } from '@/api/axiosClient'
import { API_BASE_URL } from '@/lib/constants'
import { useAuth } from '@/context/AuthContext'

export function useOperatorWebSocket() {
  const queryClient = useQueryClient()
  const { isAuthenticated } = useAuth()
  const retryDelayRef = useRef(1000)
  const timerRef = useRef<any>(null)

  useEffect(() => {
    if (!isAuthenticated) return
    let closedByUnmount = false
    let ws: WebSocket | null = null

    const connect = () => {
      const token = tokenStore.accessToken
      if (!token || closedByUnmount) return

      // API_BASE_URL may end with /api/v1; /ws/operator lives at root
      const rootOrigin = API_BASE_URL.replace(/\/api\/v1\/?$/, '').replace(/^http/, 'ws')
      const wsUrl = `${rootOrigin}/ws/operator?token=${encodeURIComponent(token)}`

      try {
        ws = new WebSocket(wsUrl)
        ws.onopen = () => {
          retryDelayRef.current = 1000
        }
        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data)
            const ev = msg?.event
            if (ev === 'sos.created') {
              queryClient.invalidateQueries({ queryKey: ['sos'] })
              toast.error(
                `NEW ${(msg.alert_type || 'SOS').replace('_', ' ').toUpperCase()} (${msg.service_category || 'general'})`,
                { duration: 6000 },
              )
            } else if (ev === 'sos.updated' || ev === 'sos.cancelled') {
              queryClient.invalidateQueries({ queryKey: ['sos'] })
            } else if (ev === 'track.updated') {
              queryClient.invalidateQueries({ queryKey: ['operator-track-list'] })
              queryClient.invalidateQueries({ queryKey: ['operator-track-detail'] })
            } else if (ev === 'report.created') {
              queryClient.invalidateQueries({ queryKey: ['emergency-calls'] })
            }
          } catch {}
        }
        ws.onclose = () => {
          if (closedByUnmount) return
          const delay = retryDelayRef.current
          retryDelayRef.current = Math.min(delay * 2, 30000)
          timerRef.current = setTimeout(connect, delay)
        }
      } catch {
        const delay = retryDelayRef.current
        retryDelayRef.current = Math.min(delay * 2, 30000)
        timerRef.current = setTimeout(connect, delay)
      }
    }

    connect()
    return () => {
      closedByUnmount = true
      clearTimeout(timerRef.current)
      try { ws?.close() } catch {}
    }
  }, [isAuthenticated, queryClient])
}
