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

  it('renders structured plan columns', () => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    expect(screen.getByRole('button', { name: 'Program' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Payer Code' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Category' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Notes' })).toBeInTheDocument()
    expect(screen.getByText('DC MEDICAID FFS')).toBeInTheDocument()
    expect(screen.getByText('853Q')).toBeInTheDocument()
    expect(screen.getByText('BUY-IN')).toBeInTheDocument()
    expect(screen.getAllByText('Coverage on file').length).toBeGreaterThan(0)
  })

  it('switches between agency, primary, Medicare, and all-plan columns', () => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={[multiPlanResult()]}
        summary={{ total: 1, active: 1, inactive: 0, error: 0, notFound: 0, unknown: 0 }}
      />,
    )

    expect(screen.getByText('DC MEDICAID FFS')).toBeInTheDocument()
    expect(screen.getByText('853Q')).toBeInTheDocument()
    expect(screen.queryByText('ON-FILE')).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Plan view'), {
      target: { value: 'primary' },
    })
    expect(screen.getByText('MEDICARE PRIMARY')).toBeInTheDocument()
    expect(screen.getByText('ON-FILE')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Plan view'), {
      target: { value: 'all' },
    })
    expect(screen.getByText('MEDICARE PRIMARY')).toBeInTheDocument()
    expect(screen.getByText('DC MEDICAID FFS')).toBeInTheDocument()
    expect(screen.getByText('ON-FILE')).toBeInTheDocument()
    expect(screen.getByText('853Q')).toBeInTheDocument()
  })

  it('searches structured plan fields', () => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    fireEvent.change(screen.getByLabelText('Search'), {
      target: { value: 'BUY-IN' },
    })

    expect(screen.getByText('SMITH, JOHN')).toBeInTheDocument()
    expect(screen.queryByText('DOE, JANE')).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Search'), {
      target: { value: '853Q' },
    })

    expect(screen.getByText('SMITH, JOHN')).toBeInTheDocument()
    expect(screen.queryByText('DOE, JANE')).not.toBeInTheDocument()
  })

  it('keeps the export button reachable on narrow layouts', () => {
    render(
      <EligibilityDashboard
        onExport={vi.fn()}
        results={eligibilityResultsFixture}
        summary={eligibilitySummaryFixture}
      />,
    )

    expect(screen.getByRole('button', { name: /Export Excel/ })).toHaveClass('w-full', 'sm:w-auto')
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

    expect(screen.getAllByText('Coverage on file').length).toBeGreaterThan(0)
    expect(screen.getByText('P5 Plan Sponsor')).toBeInTheDocument()
    expect(screen.getByText('GAINWELL PLAN SPONSOR')).toBeInTheDocument()
    expect(screen.getByText('TE:8005550100')).toBeInTheDocument()
    expect(screen.getByText('EM:plans@example.test')).toBeInTheDocument()
  })
})

function multiPlanResult() {
  return {
    memberName: 'PLAN, SWITCH',
    memberId: 'SUB000001',
    overallStatus: 'active',
    statusReason: 'Coverage on file',
    stControlNumber: '0001',
    traceNumber: 'TRACE000001',
    eligibilitySegments: [
      {
        eligibilityCode: '1',
        serviceTypeCode: '30',
        serviceTypeCodes: ['30'],
        coverageLevelCode: null,
        insuranceTypeCode: 'MB',
        planCoverageDescription: 'MEDICARE PRIMARY | ON-FILE | MEDICARE',
        monetaryAmount: null,
        quantity: null,
        inPlanNetworkIndicator: null,
      },
      {
        eligibilityCode: '1',
        serviceTypeCode: '30',
        serviceTypeCodes: ['30'],
        coverageLevelCode: null,
        insuranceTypeCode: 'MC',
        planCoverageDescription: 'DC MEDICAID FFS | 853Q | BUY-IN',
        monetaryAmount: null,
        quantity: null,
        inPlanNetworkIndicator: null,
      },
    ],
    benefitEntities: [],
    aaaErrors: [],
  } as const
}
