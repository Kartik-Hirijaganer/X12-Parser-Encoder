import { cn } from '../../utils/cn'

type BadgeVariant = 'active' | 'inactive' | 'warning' | 'notfound' | 'snip'

export function Badge({
  children,
  className,
  variant,
}: {
  children: React.ReactNode
  className?: string
  variant: BadgeVariant
}) {
  return (
    <span className={cn(badgeBaseClass, badgeVariantClasses[variant], className)}>{children}</span>
  )
}

const badgeBaseClass =
  'inline-flex items-center rounded-[var(--radius-pill)] px-2.5 py-1 text-[12px] font-semibold tracking-[0.02em]'

const badgeVariantClasses: Record<BadgeVariant, string> = {
  active: 'bg-[var(--color-active-50)] text-[var(--color-active-500)]',
  inactive: 'bg-[var(--color-inactive-50)] text-[var(--color-inactive-500)]',
  warning: 'bg-[var(--color-warning-50)] text-[var(--color-warning-500)]',
  notfound: 'bg-[var(--color-notfound-50)] text-[var(--color-notfound-500)]',
  snip: 'rounded-[var(--radius-sm)] border border-[var(--color-border-default)] bg-[var(--color-surface-secondary)] font-mono text-[var(--color-notfound-500)]',
}
