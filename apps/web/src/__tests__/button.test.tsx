import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Button } from '../components/ui/Button'

describe('Button', () => {
  it('renders text, fires onClick, and applies variant classes', () => {
    const handleClick = vi.fn()

    render(
      <Button onClick={handleClick} variant="primary">
        Save Changes
      </Button>,
    )

    const button = screen.getByRole('button', { name: 'Save Changes' })
    fireEvent.click(button)

    expect(handleClick).toHaveBeenCalledTimes(1)
    expect(button.className).toContain('bg-[var(--color-action-500)]')
  })
})
