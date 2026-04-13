import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Badge } from '../components/ui/Badge'

describe('Badge', () => {
  it('renders the correct variant classes', () => {
    render(<Badge variant="active">ACTIVE</Badge>)

    const badge = screen.getByText('ACTIVE')
    expect(badge.className).toContain('bg-[var(--color-active-50)]')
    expect(badge.className).toContain('text-[var(--color-active-500)]')
  })
})
