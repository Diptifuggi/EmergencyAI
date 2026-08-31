// @ts-nocheck
import { toast } from '@/hooks/use-toast'

export const toastSuccess = (msg: string, title = 'Success') => toast({ title, description: msg })
export const toastError = (msg: string, title = 'Error') => toast({ title, description: msg, variant: 'destructive' })
export const toastInfo = (msg: string) => toast({ title: 'Info', description: msg })
export const toastPipeline = (priority: string, score: number) => toast({ title: 'Pipeline Complete', description: `Priority: ${priority} · Score: ${score}/100` })

export default {
  toastSuccess,
  toastError,
  toastInfo,
  toastPipeline,
}
