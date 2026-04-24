import type { CSSProperties } from 'react'

import { cn } from '../../utils/cn'

type ProgressBarVariant = 'determinate' | 'indeterminate'

interface ProgressBarProps {
  variant?: ProgressBarVariant
  value?: number
  label?: string
  className?: string
}

export function ProgressBar({
  className,
  label,
  value,
  variant = 'determinate',
}: ProgressBarProps) {
  const clamped = variant === 'determinate' ? Math.max(0, Math.min(100, value ?? 0)) : undefined
  const indeterminate = variant === 'indeterminate'
  const fillStyle: CSSProperties = indeterminate
    ? {}
    : { width: `${clamped}%` }

  return (
    <div
      aria-label={label}
      aria-valuemax={indeterminate ? undefined : 100}
      aria-valuemin={indeterminate ? undefined : 0}
      aria-valuenow={indeterminate ? undefined : clamped}
      className={cn(trackClass, className)}
      role="progressbar"
    >
      <span
        className={cn(fillBaseClass, indeterminate ? indeterminateClass : determinateClass)}
        style={fillStyle}
      />
    </div>
  )
}

const trackClass =
  'relative h-2 w-full overflow-hidden rounded-[var(--radius-pill)] bg-[var(--color-surface-secondary)]'

const fillBaseClass =
  'block h-full rounded-[var(--radius-pill)] bg-[var(--color-action-500)]'

const determinateClass =
  'transition-[width] duration-[var(--duration-normal)] ease-[var(--ease-out)]'

const indeterminateClass =
  'absolute left-0 top-0 w-1/3 animate-[progressbar-slide_1.2s_ease-in-out_infinite]'
