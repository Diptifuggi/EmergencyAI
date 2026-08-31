// @ts-nocheck
import * as React from "react"
import { cn } from "@/lib/utils"

export function Textarea({ className = '', ...props }) {
	return (
		<textarea
			data-slot="textarea"
			className={cn(
				'min-h-[80px] w-full rounded-lg border border-input bg-transparent px-3 py-2 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50',
				className
			)}
			{...props}
		/>
	)
}

export default Textarea
