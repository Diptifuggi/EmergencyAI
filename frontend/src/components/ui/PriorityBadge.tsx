// @ts-nocheck
import * as React from "react"
import { cn } from "@/lib/utils"
import { getPriorityConfig } from "@/lib/priorityUtils"

function PriorityBadge({ value, className, ...props }) {
  const config = getPriorityConfig(value)
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold",
        className
      )}
      style={{ backgroundColor: config.color, color: "white" }}
      {...props}
    >
      {value}
    </span>
  )
}

export { PriorityBadge }
export default PriorityBadge
