import * as Dialog from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'

import { Button } from './Button'
import { CloseIcon } from './Icons'
import { cn } from '../../utils/cn'

interface ModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
  className?: string
  closeLabel?: string
}

export function Modal({
  children,
  className,
  closeLabel = 'Close dialog',
  description,
  footer,
  onOpenChange,
  open,
  title,
}: ModalProps) {
  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Portal>
        <Dialog.Overlay className={cn('ui-dialog-overlay', overlayClass)} />
        <Dialog.Content className={cn('ui-dialog-content', contentClass, className)}>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-2">
              <Dialog.Title className="text-lg font-semibold text-[var(--color-text-primary)]">
                {title}
              </Dialog.Title>
              {description ? (
                <Dialog.Description className="text-sm text-[var(--color-text-secondary)]">
                  {description}
                </Dialog.Description>
              ) : null}
            </div>
            <Dialog.Close asChild>
              <Button aria-label={closeLabel} size="icon" variant="quiet">
                <CloseIcon className="h-4 w-4" />
              </Button>
            </Dialog.Close>
          </div>
          {children ? <div className="text-sm text-[var(--color-text-primary)]">{children}</div> : null}
          {footer ? <div className="flex flex-wrap justify-end gap-2">{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

const overlayClass =
  'fixed inset-0 z-40 bg-[var(--color-surface-dark)]/60'

const contentClass =
  'fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[92vw] max-w-md -translate-x-1/2 -translate-y-1/2 flex-col gap-4 overflow-y-auto rounded-[var(--radius-xl)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] p-6 shadow-[var(--shadow-xl)] focus:outline-none'
