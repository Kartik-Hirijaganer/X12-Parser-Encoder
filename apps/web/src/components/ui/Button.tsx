import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '../../utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'quiet' | 'table'
type ButtonSize = 'sm' | 'md' | 'icon'

interface CommonProps {
  children: ReactNode
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}

type LinkButtonProps = CommonProps &
  AnchorHTMLAttributes<HTMLAnchorElement> & {
    href: string
  }

type NativeButtonProps = CommonProps &
  ButtonHTMLAttributes<HTMLButtonElement> & {
    href?: never
  }

export function Button(props: LinkButtonProps | NativeButtonProps) {
  const {
    children,
    className,
    leftIcon,
    rightIcon,
    size = 'md',
    variant = 'primary',
    ...rest
  } = props

  const classes = cn(buttonBaseClass, buttonVariantClasses[variant], buttonSizeClasses[size], className)

  if ('href' in props) {
    const anchorProps = rest as AnchorHTMLAttributes<HTMLAnchorElement>
    return (
      <a className={classes} {...anchorProps}>
        {leftIcon}
        <span>{children}</span>
        {rightIcon}
      </a>
    )
  }

  const buttonProps = rest as ButtonHTMLAttributes<HTMLButtonElement>
  return (
    <button className={classes} type="button" {...buttonProps}>
      {leftIcon}
      <span>{children}</span>
      {rightIcon}
    </button>
  )
}

const buttonBaseClass =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-pill)] font-medium transition-[background-color,border-color,box-shadow,transform,color] duration-[var(--duration-normal)] ease-[var(--ease-out)] focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-[var(--color-focus-ring)] disabled:cursor-not-allowed disabled:border-[var(--color-border-default)] disabled:bg-[var(--color-border-default)] disabled:text-[var(--color-text-disabled)] disabled:shadow-none'

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--color-action-500)] px-6 py-2.5 text-[14px] text-[var(--color-text-inverse)] shadow-[var(--shadow-md)] hover:bg-[var(--color-action-600)] hover:shadow-[var(--shadow-lg)] hover:translate-y-[-1px] active:translate-y-0 active:bg-[var(--color-action-700)]',
  secondary:
    'border-2 border-[var(--color-border-default)] bg-transparent px-6 py-2.5 text-[14px] text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-secondary)]',
  ghost:
    'rounded-[var(--radius-md)] px-4 py-2 text-[14px] text-[var(--color-action-500)] hover:bg-[var(--color-action-50)]',
  quiet:
    'rounded-[var(--radius-md)] px-3 py-2 text-[13px] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-secondary)] hover:text-[var(--color-text-primary)]',
  table:
    'min-h-0 rounded-[var(--radius-md)] px-0 py-0 text-left text-[13px] font-semibold uppercase tracking-[0.04em] text-[var(--color-text-primary)] hover:text-[var(--color-action-500)]',
}

const buttonSizeClasses: Record<ButtonSize, string> = {
  sm: 'min-h-9 px-4 py-2 text-[13px]',
  md: '',
  icon: 'min-h-10 min-w-10 rounded-[var(--radius-md)] px-2 py-2',
}
