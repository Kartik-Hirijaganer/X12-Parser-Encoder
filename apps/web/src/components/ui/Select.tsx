import type { SelectHTMLAttributes } from 'react'

import { cn } from '../../utils/cn'
import { ChevronDownIcon } from './Icons'

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  wrapperClassName?: string
}

export function Select({ children, className, wrapperClassName, ...props }: SelectProps) {
  return (
    <span className={cn('relative inline-flex w-full', wrapperClassName)}>
      <select className={cn(selectClass, className)} {...props}>
        {children}
      </select>
      <ChevronDownIcon className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-tertiary)]" />
    </span>
  )
}

const selectClass =
  'min-h-11 w-full appearance-none rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] px-3 py-2 pr-10 text-base text-[var(--color-text-primary)] transition-[border-color,box-shadow] duration-[var(--duration-fast)] ease-[var(--ease-out)] focus:border-[var(--color-action-500)] focus:outline-none focus:ring-[var(--focus-ring-width)] focus:ring-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:bg-[var(--color-surface-secondary)] disabled:text-[var(--color-text-disabled)]'
