import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { EligibilityDashboard } from '../components/features/EligibilityDashboard'
import { eligibilityResultsFixture, eligibilitySummaryFixture } from './fixtures'

describe('EligibilityDashboard', () => {
  it('shows the correct stat card counts', () => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    expect(screen.getAllByText('Active')[0].closest('section')).toHaveTextContent('1')
    expect(screen.getAllByText('Inactive')[0].closest('section')).toHaveTextContent('1')
    expect(screen.getAllByText('Errors')[0].closest('section')).toHaveTextContent('1')
    expect(screen.getAllByText('Not Found')[0].closest('section')).toHaveTextContent('0')
  })

  it('filters rows by status and triggers export', () => {
    const onExport = vi.fn()
    render(
      <EligibilityDashboard
        onExport={onExport}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    fireEvent.change(screen.getByLabelText('Filter'), {
      target: { value: 'active' },
    })

    expect(screen.getByText('SMITH, JOHN')).toBeInTheDocument()
    expect(screen.queryByText('DOE, JANE')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Export Excel' }))
    expect(onExport).toHaveBeenCalledTimes(1)
  })
})
