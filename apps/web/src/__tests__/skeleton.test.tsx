import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Skeleton } from '../components/ui/Skeleton'

describe('Skeleton', () => {
  it('renders a labelled busy indicator with token-driven radius', () => {
    render(<Skeleton aria-label="Loading rows" height="2rem" radius="lg" width="120px" />)

    const skeleton = screen.getByRole('status', { name: 'Loading rows' })
    expect(skeleton).toHaveAttribute('aria-busy', 'true')
    expect(skeleton).toHaveStyle({ width: '120px', height: '2rem' })
    expect(skeleton.style.borderRadius).toBe('var(--radius-lg)')
  })
})
