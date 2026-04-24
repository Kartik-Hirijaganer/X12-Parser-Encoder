/* eslint-disable react-refresh/only-export-components */
import { Toaster as SonnerToaster, toast as sonnerToast, type ToasterProps } from 'sonner'

import { useReducedMotionPreference } from '../../hooks/useReducedMotionPreference'
import { cn } from '../../utils/cn'

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
  const prefersReducedMotion = useReducedMotionPreference()

  return (
    <SonnerToaster
      className={cn(prefersReducedMotion && 'ui-toast-reduced-motion')}
      closeButton
      position="bottom-right"
      richColors
      swipeDirections={prefersReducedMotion ? [] : undefined}
      toastOptions={{
        className: prefersReducedMotion ? 'ui-toast-reduced-motion' : undefined,
        style: {
          fontFamily: 'var(--font-sans)',
          borderRadius: 'var(--radius-md)',
          transition: prefersReducedMotion ? 'none' : undefined,
        },
      }}
      {...props}
    />
  )
}
