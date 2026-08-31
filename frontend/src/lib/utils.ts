// @ts-nocheck
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: Parameters<typeof clsx>): string {
  return twMerge(clsx(...(inputs as any)))
}

export default cn
