import { Button } from './Button'
import { cn } from '../../utils/cn'

interface UnsavedChangesBarProps {
  className?: string
  message?: string
  onDiscard: () => void
  onSave: () => void
  saveDisabled?: boolean
}

export function UnsavedChangesBar({
  className,
  message = 'You have unsaved settings changes.',
  onDiscard,
  onSave,
  saveDisabled = false,
}: UnsavedChangesBarProps) {
  return (
    <div className={cn(unsavedChangesBarClass, className)} role="status">
      <p className="text-sm font-medium text-[var(--color-text-primary)]">{message}</p>
      <div className="flex flex-wrap gap-2">
        <Button onClick={onDiscard} variant="secondary">
          Discard
        </Button>
        <Button disabled={saveDisabled} onClick={onSave} variant="primary">
          Save Changes
        </Button>
      </div>
    </div>
  )
}

const unsavedChangesBarClass =
  'sticky bottom-4 z-10 mx-auto flex max-w-[var(--layout-settings-max)] flex-wrap items-center justify-between gap-3 rounded-[var(--radius-xl)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] px-4 py-3 shadow-[var(--shadow-lg)]'
