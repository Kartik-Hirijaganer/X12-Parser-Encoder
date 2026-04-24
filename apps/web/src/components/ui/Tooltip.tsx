import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import type { ReactNode } from 'react'

import { cn } from '../../utils/cn'

interface TooltipProps {
  content: ReactNode
  children: ReactNode
  side?: 'top' | 'right' | 'bottom' | 'left'
  align?: 'start' | 'center' | 'end'
  delayDuration?: number
  className?: string
}

export function Tooltip({
  align = 'center',
  children,
  className,
  content,
  delayDuration = 300,
  side = 'top',
}: TooltipProps) {
  return (
    <TooltipPrimitive.Provider delayDuration={delayDuration}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            align={align}
            className={cn(tooltipContentClass, className)}
            side={side}
            sideOffset={6}
          >
            {content}
            <TooltipPrimitive.Arrow className="fill-[var(--color-surface-dark)]" />
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  )
}

const tooltipContentClass =
  'z-50 max-w-xs rounded-[var(--radius-md)] bg-[var(--color-surface-dark)] px-3 py-2 text-caption text-[var(--color-text-inverse)] shadow-[var(--shadow-lg)]'
