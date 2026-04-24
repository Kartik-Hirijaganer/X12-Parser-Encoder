import * as Dialog from '@radix-ui/react-dialog'
import type { ReactNode } from 'react'

import { Button } from './Button'
import { CloseIcon } from './Icons'
import { useReducedMotionPreference } from '../../hooks/useReducedMotionPreference'
import { cn } from '../../utils/cn'

type DrawerSide = 'left' | 'right'

interface DrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  children?: ReactNode
  footer?: ReactNode
  side?: DrawerSide
  className?: string
  closeLabel?: string
}

export function Drawer({
  children,
  className,
  closeLabel = 'Close drawer',
  description,
  footer,
  onOpenChange,
  open,
  side = 'right',
  title,
}: DrawerProps) {
  const prefersReducedMotion = useReducedMotionPreference()

  return (
    <Dialog.Root onOpenChange={onOpenChange} open={open}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn('ui-dialog-overlay', overlayClass)}
          data-reduced-motion={prefersReducedMotion}
        />
        <Dialog.Content
          className={cn('ui-drawer-content', contentBaseClass, sideClasses[side], className)}
          data-reduced-motion={prefersReducedMotion}
          data-side={side}
        >
          <div className="flex items-start justify-between gap-4 border-b border-[var(--color-border-default)] pb-4">
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
          {children ? <div className="flex-1 overflow-y-auto text-sm text-[var(--color-text-primary)]">{children}</div> : null}
          {footer ? (
            <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--color-border-default)] pt-4">
              {footer}
            </div>
          ) : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

const overlayClass = 'fixed inset-0 z-40 bg-[var(--color-surface-dark)]/60'

const contentBaseClass =
  'fixed top-0 bottom-0 z-50 flex h-full w-[92vw] max-w-md flex-col gap-4 border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] p-6 shadow-[var(--shadow-xl)] focus:outline-none'

const sideClasses: Record<DrawerSide, string> = {
  right: 'right-0',
  left: 'left-0',
}
