// @ts-nocheck
import * as React from "react"
import { cn } from "@/lib/utils"

const Select = React.forwardRef(({ className, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-10 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none transition-all focus:border-ring focus:ring-2 focus:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  />
))

Select.displayName = "Select"

export { Select }
export default Select
