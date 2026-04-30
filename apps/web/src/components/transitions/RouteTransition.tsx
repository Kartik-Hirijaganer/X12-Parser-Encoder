import type { ReactNode } from 'react'
import { useMemo } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useLocation } from 'react-router-dom'

import { useReducedMotionPreference } from '../../hooks/useReducedMotionPreference'

export function RouteTransition({ children }: { children: ReactNode }) {
  const location = useLocation()
  const prefersReducedMotion = useReducedMotionPreference()
  const motionTokens = useMemo(() => readRouteMotionTokens(), [])

  const transition = prefersReducedMotion
    ? { duration: 0 }
    : { duration: motionTokens.durationSeconds, ease: [0.16, 1, 0.3, 1] as const }

  const initial = prefersReducedMotion ? false : { opacity: 0, y: motionTokens.slideOffsetPx }
  const animate = prefersReducedMotion ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }
  const exit = prefersReducedMotion ? { opacity: 1 } : { opacity: 0, y: -motionTokens.slideOffsetPx }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        animate={animate}
        exit={exit}
        initial={initial}
        key={location.pathname}
        transition={transition}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}

function readRouteMotionTokens(): { durationSeconds: number; slideOffsetPx: number } {
  if (typeof window === 'undefined') {
    return { durationSeconds: 0.2, slideOffsetPx: 6 }
  }

  const styles = window.getComputedStyle(document.documentElement)
  return {
    durationSeconds: parseDurationSeconds(styles.getPropertyValue('--duration-route'), 0.2),
    slideOffsetPx: parsePixelValue(styles.getPropertyValue('--motion-route-slide'), 6),
  }
}

function parseDurationSeconds(rawValue: string, fallback: number): number {
  const value = rawValue.trim()
  if (value.endsWith('ms')) {
    const parsed = Number(value.slice(0, -2))
    return Number.isFinite(parsed) ? parsed / 1000 : fallback
  }
  if (value.endsWith('s')) {
    const parsed = Number(value.slice(0, -1))
    return Number.isFinite(parsed) ? parsed : fallback
  }
  return fallback
}

function parsePixelValue(rawValue: string, fallback: number): number {
  const parsed = Number(rawValue.trim().replace(/px$/, ''))
  return Number.isFinite(parsed) ? parsed : fallback
}
