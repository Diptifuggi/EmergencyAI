// @ts-nocheck
import * as React from 'react'
import { cn } from '@/lib/utils'

export interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  icon: React.ReactNode
  iconBg?: string
  label: React.ReactNode
  value: React.ReactNode
  delta?: number
  deltaDirection?: 'up' | 'down'
}

function StatCard({ icon, iconBg = 'bg-slate-100', label, value, delta, deltaDirection = 'up', className, ...props }: StatCardProps) {
  return (
    <div className={cn("rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900", className)} {...props}>
      <div className="flex items-center justify-between gap-4">
        <div className={cn("flex h-11 w-11 items-center justify-center rounded-2xl", iconBg)}>{icon}</div>
        <div className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500 dark:text-slate-400">{label}</div>
      </div>
      <div className="mt-6 flex items-end justify-between gap-4">
        <div>
          <div className="text-3xl font-semibold text-slate-950 dark:text-white">{value}</div>
          {typeof delta === "number" ? (
            <div className="text-sm text-slate-500 dark:text-slate-400">
              {deltaDirection === "up" ? "↑" : "↓"} {Math.abs(delta)}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export { StatCard }
export default StatCard
