import type { ReactNode } from 'react'

import { Button } from './Button'
import { Modal } from './Modal'

interface ConfirmationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
  onConfirm: () => void
  onCancel?: () => void
  children?: ReactNode
}

export function ConfirmationDialog({
  cancelLabel = 'Cancel',
  children,
  confirmLabel = 'Confirm',
  description,
  destructive = false,
  onCancel,
  onConfirm,
  onOpenChange,
  open,
  title,
}: ConfirmationDialogProps) {
  const handleCancel = () => {
    onCancel?.()
    onOpenChange(false)
  }

  const handleConfirm = () => {
    onConfirm()
    onOpenChange(false)
  }

  return (
    <Modal
      description={description}
      footer={
        <>
          <Button onClick={handleCancel} variant="secondary">
            {cancelLabel}
          </Button>
          <Button
            className={destructive ? destructiveButtonClass : undefined}
            onClick={handleConfirm}
            variant="primary"
          >
            {confirmLabel}
          </Button>
        </>
      }
      onOpenChange={onOpenChange}
      open={open}
      title={title}
    >
      {children}
    </Modal>
  )
}

const destructiveButtonClass =
  'bg-[var(--color-inactive-500)] hover:bg-[var(--color-inactive-500)] active:bg-[var(--color-inactive-500)] shadow-[var(--shadow-md)]'
