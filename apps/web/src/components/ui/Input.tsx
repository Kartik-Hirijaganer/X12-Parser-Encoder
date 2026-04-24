import type { InputHTMLAttributes } from 'react'

import { cn } from '../../utils/cn'

type InputProps = InputHTMLAttributes<HTMLInputElement>

export function Input({ className, type = 'text', ...props }: InputProps) {
  return <input className={cn(inputClass, className)} type={type} {...props} />
}

const inputClass =
  'min-h-11 w-full rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] px-3 py-2 text-base text-[var(--color-text-primary)] transition-[border-color,box-shadow] duration-[var(--duration-fast)] ease-[var(--ease-out)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-action-500)] focus:outline-none focus:ring-[var(--focus-ring-width)] focus:ring-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:bg-[var(--color-surface-secondary)] disabled:text-[var(--color-text-disabled)]'
