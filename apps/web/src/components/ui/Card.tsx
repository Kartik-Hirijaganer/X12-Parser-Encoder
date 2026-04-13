import { cn } from '../../utils/cn'

type CardVariant = 'content' | 'action'

export function Card({
  children,
  className,
  variant = 'content',
}: {
  children: React.ReactNode
  className?: string
  variant?: CardVariant
}) {
  return <section className={cn(cardClasses[variant], className)}>{children}</section>
}

const sharedCardClass =
  'rounded-[var(--radius-xl)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)]'

const cardClasses: Record<CardVariant, string> = {
  content: cn(sharedCardClass, 'p-6 shadow-[var(--shadow-sm)]'),
  action: cn(
    sharedCardClass,
    'p-6 shadow-[var(--shadow-md)] transition-[box-shadow,transform] duration-[var(--duration-slow)] ease-[var(--ease-out)] hover:translate-y-[-2px] hover:shadow-[var(--shadow-lg)]',
  ),
}
