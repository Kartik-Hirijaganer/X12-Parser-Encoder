import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '../../utils/cn'

type CardVariant = 'content' | 'action'

type NativeButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  'children' | 'className' | 'type'
>

interface CardSectionProps {
  children: ReactNode
  className?: string
  variant?: CardVariant
  as?: 'section'
}

interface CardButtonProps extends NativeButtonProps {
  children: ReactNode
  className?: string
  variant?: CardVariant
  as: 'button'
}

export function Card(props: CardSectionProps | CardButtonProps) {
  const variant: CardVariant = props.variant ?? 'content'

  if (props.as === 'button') {
    const { as, children, className, variant: _variant, ...buttonProps } = props
    void as
    void _variant
    return (
      <button
        className={cn(cardClasses[variant], 'text-left', className)}
        type="button"
        {...buttonProps}
      >
        {children}
      </button>
    )
  }

  return (
    <section className={cn(cardClasses[variant], props.className)}>{props.children}</section>
  )
}

const sharedCardClass =
  'rounded-[var(--radius-xl)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)]'

const cardClasses: Record<CardVariant, string> = {
  content: cn(sharedCardClass, 'p-6 shadow-[var(--shadow-sm)]'),
  action: cn(
    sharedCardClass,
    'p-6 shadow-[var(--shadow-md)] transition-[box-shadow,transform] duration-[var(--duration-slow)] ease-[var(--ease-out)] hover:translate-y-[var(--motion-lift-md)] hover:shadow-[var(--shadow-lg)]',
  ),
}
