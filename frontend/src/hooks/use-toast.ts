// @ts-nocheck
import * as React from 'react'

type ToastItem = {
  id: string
  title: string
  description?: string
  variant?: string
  action?: any
}

const listeners = new Set<(toasts: ToastItem[]) => void>()
let toasts: ToastItem[] = []
let toastId = 0

function notify() {
  listeners.forEach((listener) => listener([...toasts]))
}

export function toast({ title, description, variant = 'default', action, duration = 4000 }: { title: string; description?: string; variant?: string; action?: any; duration?: number }) {
  const id = `toast-${++toastId}`
  const toastItem: ToastItem = {
    id,
    title,
    description,
    variant,
    action,
  }

  toasts = [...toasts, toastItem]
  notify()

  if (duration > 0) {
    window.setTimeout(() => {
      toasts = toasts.filter((item) => item.id !== id)
      notify()
    }, duration)
  }

  return id
}

export function useToast() {
  const [state, setState] = React.useState<ToastItem[]>(toasts)

  React.useEffect(() => {
    const listener = (nextToasts: ToastItem[]) => setState(nextToasts)
    listeners.add(listener)
    listener(toasts)
    return () => {
      listeners.delete(listener)
    }
  }, [])

  return { toasts: state }
}
