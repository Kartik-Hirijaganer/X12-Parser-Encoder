import { Button } from './Button'
import { CheckIcon, CloseIcon, InfoIcon, WarningIcon } from './Icons'
import { cn } from '../../utils/cn'

type BannerVariant = 'info' | 'warning' | 'error' | 'success'

export function Banner({
  actions,
  children,
  className,
  dismissLabel = 'Dismiss',
  onDismiss,
  title,
  variant,
}: {
  actions?: React.ReactNode
  children: React.ReactNode
  className?: string
  dismissLabel?: string
  onDismiss?: () => void
  title?: string
  variant: BannerVariant
}) {
  const Icon = bannerIcons[variant]
  return (
    <div className={cn(bannerBaseClass, bannerVariantClasses[variant], className)} role="status">
      <div className="mt-0.5">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        {title ? <p className="text-sm font-semibold">{title}</p> : null}
        <div className="text-sm leading-6">{children}</div>
        {actions ? <div className="mt-3 flex flex-wrap gap-2">{actions}</div> : null}
      </div>
      {onDismiss ? (
        <Button
          aria-label={dismissLabel}
          className="self-start"
          onClick={onDismiss}
          size="icon"
          variant="quiet"
        >
          <CloseIcon className="h-4 w-4" />
        </Button>
      ) : null}
    </div>
  )
}

const bannerBaseClass =
  'flex items-start gap-3 rounded-[var(--radius-md)] border-l-4 px-4 py-3 text-[var(--color-text-primary)]'

const bannerVariantClasses: Record<BannerVariant, string> = {
  info: 'border-[var(--color-action-500)] bg-[var(--color-action-50)] text-[var(--color-text-primary)]',
  warning:
    'border-[var(--color-warning-500)] bg-[var(--color-warning-50)] text-[var(--color-text-primary)]',
  error:
    'border-[var(--color-inactive-500)] bg-[var(--color-inactive-50)] text-[var(--color-inactive-500)]',
  success:
    'border-[var(--color-active-500)] bg-[var(--color-active-50)] text-[var(--color-text-primary)]',
}

const bannerIcons = {
  info: InfoIcon,
  warning: WarningIcon,
  error: WarningIcon,
  success: CheckIcon,
}
