import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ProgressBar } from '../components/ui/ProgressBar'

describe('ProgressBar', () => {
  it('renders determinate progress with clamped aria values', () => {
    render(<ProgressBar label="Uploading" value={150} variant="determinate" />)

    const bar = screen.getByRole('progressbar', { name: 'Uploading' })
    expect(bar).toHaveAttribute('aria-valuemin', '0')
    expect(bar).toHaveAttribute('aria-valuemax', '100')
    expect(bar).toHaveAttribute('aria-valuenow', '100')
  })

  it('omits aria value attributes when indeterminate', () => {
    render(<ProgressBar label="Processing" variant="indeterminate" />)

    const bar = screen.getByRole('progressbar', { name: 'Processing' })
    expect(bar).not.toHaveAttribute('aria-valuenow')
    expect(bar).not.toHaveAttribute('aria-valuemin')
    expect(bar).not.toHaveAttribute('aria-valuemax')
  })
})
