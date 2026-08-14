// @ts-nocheck
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"

import { cn } from "@/lib/utils"

function badgeVariants() {
	// simplified: caller may rely on styles applied via className
	return ''
}

function Badge({ className, variant = "default", asChild = false, ...props }) {
	const Comp = asChild ? Slot.Root : "span"

	return (
		<Comp
			data-slot="badge"
			data-variant={variant}
			className={cn(badgeVariants({ variant }), className)}
			{...props}
		/>
	)
}

export { Badge, badgeVariants }
