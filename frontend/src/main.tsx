// @ts-nocheck
// Opt-in to React Router v7 future flags to suppress upgrade warnings
// These flags should be set before react-router is imported/executed.
// They are non-destructive and only affect dev-time warnings.
if (typeof window !== 'undefined') {
  // @ts-ignore
  window.__RR__ = window.__RR__ || {}
  // @ts-ignore
  window.__RR__.v7_startTransition = true
  // @ts-ignore
  window.__RR__.v7_relativeSplatPath = true
}

import React from 'react'
import ReactDOM from 'react-dom/client'
import { Chart, registerables } from 'chart.js'
// Import the explicit JSX/TSX entry to avoid accidental resolution issues
import App from '@/App'
import '@/index.css'

Chart.register(...registerables)

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
