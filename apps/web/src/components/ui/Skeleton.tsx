import type { CSSProperties } from 'react'

import { useReducedMotionPreference } from '../../hooks/useReducedMotionPreference'
import { cn } from '../../utils/cn'

type RadiusToken = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'pill'

interface SkeletonProps {
  width?: string
  height?: string
  radius?: RadiusToken
  className?: string
  'aria-label'?: string
}

export function Skeleton({
  width = '100%',
  height = '1rem',
  radius = 'md',
  className,
  'aria-label': ariaLabel = 'Loading',
}: SkeletonProps) {
  const prefersReducedMotion = useReducedMotionPreference()
  const style: CSSProperties = {
    width,
    height,
    borderRadius: `var(--radius-${radius})`,
  }

  return (
    <span
      aria-busy="true"
      aria-label={ariaLabel}
      className={cn(
        'inline-block bg-[var(--color-surface-secondary)]',
        !prefersReducedMotion && 'animate-pulse',
        className,
      )}
      role="status"
      style={style}
    />
  )
}
