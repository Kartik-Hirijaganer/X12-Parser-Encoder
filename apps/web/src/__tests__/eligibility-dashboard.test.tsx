import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { EligibilityDashboard } from '../components/features/EligibilityDashboard'
import { eligibilityResultsFixture, eligibilitySummaryFixture } from './fixtures'

describe('EligibilityDashboard', () => {
  it('shows all five stat card counts', () => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    expect(screen.getAllByText('Active')[0].closest('button')).toHaveTextContent('1')
    expect(screen.getAllByText('Inactive')[0].closest('button')).toHaveTextContent('1')
    expect(screen.getAllByText('Errors')[0].closest('button')).toHaveTextContent('1')
    expect(screen.getAllByText('Not Found')[0].closest('button')).toHaveTextContent('1')
    expect(screen.getAllByText('Unknown')[0].closest('button')).toHaveTextContent('1')
  })

  it.each([
    ['active', 'SMITH, JOHN'],
    ['inactive', 'DOE, JANE'],
    ['error', 'ERROR, MEMBER'],
    ['not_found', 'MISSING, MEMBER'],
    ['unknown', 'SUPPLEMENTAL, MEMBER'],
  ])('filters rows by %s status', (filterValue, expectedName) => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    fireEvent.change(screen.getByLabelText('Filter'), {
      target: { value: filterValue },
    })

    expect(screen.getByText(expectedName)).toBeInTheDocument()
    if (expectedName === 'SMITH, JOHN') {
      expect(screen.getByText('SMITH, JOHN')).toBeInTheDocument()
    } else {
      expect(screen.queryByText('SMITH, JOHN')).not.toBeInTheDocument()
    }
  })

  it('searches status reason and trace number and triggers export', () => {
    const onExport = vi.fn()
    render(
      <EligibilityDashboard
        onExport={onExport}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    fireEvent.change(screen.getByLabelText('Search'), {
      target: { value: 'TRACE-005' },
    })

    expect(screen.getByText('SUPPLEMENTAL, MEMBER')).toBeInTheDocument()
    expect(screen.queryByText('SMITH, JOHN')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Export Excel' }))
    expect(onExport).toHaveBeenCalledTimes(1)
  })

  it('expands a row with status reason and 2120C contacts', () => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    fireEvent.click(screen.getAllByRole('button', { name: 'Expand row' })[0])

    expect(screen.getByText('Coverage on file')).toBeInTheDocument()
    expect(screen.getByText('P5 Plan Sponsor')).toBeInTheDocument()
    expect(screen.getByText('GAINWELL PLAN SPONSOR')).toBeInTheDocument()
    expect(screen.getByText('TE:8005550100')).toBeInTheDocument()
    expect(screen.getByText('EM:plans@example.test')).toBeInTheDocument()
  })
})
