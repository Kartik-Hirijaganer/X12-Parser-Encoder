/* eslint-disable react-refresh/only-export-components */
import { Toaster as SonnerToaster, toast as sonnerToast, type ToasterProps } from 'sonner'

export type ToastVariant = 'success' | 'info' | 'warning' | 'error'

interface ToastOptions {
  description?: string
  duration?: number
  id?: string | number
}

export const toast = {
  success: (message: string, options?: ToastOptions) => sonnerToast.success(message, options),
  info: (message: string, options?: ToastOptions) => sonnerToast.info(message, options),
  warning: (message: string, options?: ToastOptions) => sonnerToast.warning(message, options),
  error: (message: string, options?: ToastOptions) => sonnerToast.error(message, options),
  dismiss: (id?: string | number) => sonnerToast.dismiss(id),
}

export function Toaster(props: Pick<ToasterProps, 'position' | 'richColors' | 'closeButton'> = {}) {
  return (
    <SonnerToaster
      closeButton
      position="bottom-right"
      richColors
      toastOptions={{
        style: {
          fontFamily: 'var(--font-sans)',
          borderRadius: 'var(--radius-md)',
        },
      }}
      {...props}
    />
  )
}
