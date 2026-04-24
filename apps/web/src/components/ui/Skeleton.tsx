import type { CSSProperties } from 'react'

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
  const style: CSSProperties = {
    width,
    height,
    borderRadius: `var(--radius-${radius})`,
  }

  return (
    <span
      aria-busy="true"
      aria-label={ariaLabel}
      className={cn(skeletonBaseClass, className)}
      role="status"
      style={style}
    />
  )
}

const skeletonBaseClass =
  'inline-block animate-pulse bg-[var(--color-surface-secondary)]'
