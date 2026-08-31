// @ts-nocheck
import * as React from "react"
import { cn } from "@/lib/utils"

const STATUS_CLASSES = {
  Pending: { backgroundColor: "#f59e0b", color: "#0f172a" },
  Resolved: { backgroundColor: "#10b981", color: "white" },
  Dispatched: { backgroundColor: "#3b82f6", color: "white" },
  Completed: { backgroundColor: "#14b8a6", color: "white" },
  InProgress: { backgroundColor: "#8b5cf6", color: "white" },
  Cancelled: { backgroundColor: "#ef4444", color: "white" },
}

function StatusBadge({ value, className, ...props }) {
  const style = STATUS_CLASSES[value] || { backgroundColor: "#64748b", color: "white" }
  return (
    <span
      className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", className)}
      style={style}
      {...props}
    >
      {value}
    </span>
  )
}

export { StatusBadge }
export default StatusBadge
