// @ts-nocheck
import React from 'react'

interface ConfirmDialogProps {
  open: boolean
  title?: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  confirmText?: string
  cancelText?: string
}

export default function ConfirmDialog({ open, title = 'Confirm', message, onConfirm, onCancel, confirmText = 'Yes', cancelText = 'Cancel' }: ConfirmDialogProps){
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded p-6 w-full max-w-md">
        <div className="text-lg font-semibold mb-2">{title}</div>
        <div className="text-sm text-gray-600 mb-4">{message}</div>
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} className="px-3 py-1 rounded border">{cancelText}</button>
          <button onClick={onConfirm} className="px-3 py-1 rounded bg-red-600 text-white">{confirmText}</button>
        </div>
      </div>
    </div>
  )
}
