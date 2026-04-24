import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useLocation } from 'react-router-dom'

import { useReducedMotionPreference } from '../../hooks/useReducedMotionPreference'

export function RouteTransition({ children }: { children: ReactNode }) {
  const location = useLocation()
  const prefersReducedMotion = useReducedMotionPreference()

  const transition = prefersReducedMotion
    ? { duration: 0 }
    : { duration: 0.2, ease: [0.16, 1, 0.3, 1] as const }

  const initial = prefersReducedMotion ? false : { opacity: 0, y: 6 }
  const animate = prefersReducedMotion ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }
  const exit = prefersReducedMotion ? { opacity: 1 } : { opacity: 0, y: -6 }

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
