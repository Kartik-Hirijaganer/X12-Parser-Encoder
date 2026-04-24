import type { ReactNode } from 'react'

import { cn } from '../../utils/cn'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ action, className, description, icon, title }: EmptyStateProps) {
  return (
    <div className={cn(containerClass, className)} role="status">
      {icon ? (
        <div aria-hidden="true" className="text-[var(--color-text-tertiary)]">
          {icon}
        </div>
      ) : null}
      <h3 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h3>
      {description ? (
        <p className="max-w-md text-sm text-[var(--color-text-secondary)]">{description}</p>
      ) : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  )
}

const containerClass =
  'flex flex-col items-center justify-center gap-3 rounded-[var(--radius-lg)] border border-dashed border-[var(--color-border-default)] bg-[var(--color-surface-tertiary)] px-6 py-10 text-center'
