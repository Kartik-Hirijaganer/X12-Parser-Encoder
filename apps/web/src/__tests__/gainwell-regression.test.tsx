import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { EligibilityResult, EligibilitySummary, ParseResponse } from '../types/api'

import { renderApp } from './testUtils'

const exportEligibilityWorkbookMock = vi.hoisted(() => vi.fn())
const downloadBlobMock = vi.hoisted(() => vi.fn())

vi.mock('../services/api', () => ({
  ApiError: class ApiError extends Error {
    status = 500
    suggestion = null
  },
  exportEligibilityWorkbook: exportEligibilityWorkbookMock,
}))

vi.mock('../utils/downloads', () => ({
  downloadBlob: downloadBlobMock,
}))

const EXPECTED_TOTAL = 153
const EXPECTED_ACTIVE = 136
const EXPECTED_INACTIVE = 0
const EXPECTED_ERROR = 12
const EXPECTED_NOT_FOUND = 1
const EXPECTED_UNKNOWN = 4

function buildResults(): EligibilityResult[] {
  const rows: EligibilityResult[] = []
  let index = 0
  const emit = (status: EligibilityResult['overall_status'], count: number, reason: string): void => {
    for (let i = 0; i < count; i += 1) {
      index += 1
      rows.push({
        member_name: `MEMBER${String(index).padStart(4, '0')}, TEST`,
        member_id: `SUB${String(index).padStart(6, '0')}`,
        overall_status: status,
        status_reason: reason,
        st_control_number: String(index).padStart(4, '0'),
        trace_number: `TRACE${String(index).padStart(6, '0')}`,
        eligibility_segments: [],
        benefit_entities: [],
        aaa_errors: [],
      })
    }
  }
  emit('active', EXPECTED_ACTIVE, 'Coverage on file')
  emit('error', EXPECTED_ERROR, 'Invalid/missing date of birth.')
  emit('not_found', EXPECTED_NOT_FOUND, 'Subscriber not found')
  emit('unknown', EXPECTED_UNKNOWN, 'Additional payer information only')
  return rows
}

const gainwellSummary: EligibilitySummary = {
  total: EXPECTED_TOTAL,
  active: EXPECTED_ACTIVE,
  inactive: EXPECTED_INACTIVE,
  error: EXPECTED_ERROR,
  not_found: EXPECTED_NOT_FOUND,
  unknown: EXPECTED_UNKNOWN,
}

const gainwellResponse: ParseResponse = {
  filename: 'gainwell_271_redacted.edi',
  source_transaction_count: EXPECTED_TOTAL,
  parsed_result_count: EXPECTED_TOTAL,
  parser_issue_count: 0,
  parser_issues: [],
  transaction_count: EXPECTED_TOTAL,
  summary: gainwellSummary,
  payer_name: 'GAINWELL TEST PAYER',
  results: buildResults(),
}

describe('Gainwell 271 dashboard regression', () => {
  beforeEach(() => {
    exportEligibilityWorkbookMock.mockReset()
    downloadBlobMock.mockReset()
    exportEligibilityWorkbookMock.mockResolvedValue(new Blob(['xlsx']))
  })

  it('renders all five summary cards with the expected Gainwell counts', () => {
    renderApp('/dashboard', {
      filename: 'gainwell_271_redacted.edi',
      response: gainwellResponse,
    })

    expect(
      within(screen.getAllByText('Active')[0].closest('section') as HTMLElement).getByText(
        String(EXPECTED_ACTIVE),
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getAllByText('Inactive')[0].closest('section') as HTMLElement).getByText(
        String(EXPECTED_INACTIVE),
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getAllByText('Errors')[0].closest('section') as HTMLElement).getByText(
        String(EXPECTED_ERROR),
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getAllByText('Not Found')[0].closest('section') as HTMLElement).getByText(
        String(EXPECTED_NOT_FOUND),
      ),
    ).toBeInTheDocument()
    expect(
      within(screen.getAllByText('Unknown')[0].closest('section') as HTMLElement).getByText(
        String(EXPECTED_UNKNOWN),
      ),
    ).toBeInTheDocument()
  })

  it('does not display the parser issue banner when parsed_result_count == source_transaction_count', () => {
    renderApp('/dashboard', {
      filename: 'gainwell_271_redacted.edi',
      response: gainwellResponse,
    })

    expect(screen.queryByText('Parser Issues')).not.toBeInTheDocument()
  })

  it.each([
    ['active', EXPECTED_ACTIVE],
    ['error', EXPECTED_ERROR],
    ['not_found', EXPECTED_NOT_FOUND],
    ['unknown', EXPECTED_UNKNOWN],
  ])('filters rows by %s status and preserves the matching subset', (filterValue, expectedCount) => {
    renderApp('/dashboard', {
      filename: 'gainwell_271_redacted.edi',
      response: gainwellResponse,
    })

    fireEvent.change(screen.getByLabelText('Filter'), {
      target: { value: filterValue },
    })

    const matching = gainwellResponse.results.filter(
      (result) => result.overall_status === filterValue,
    )
    expect(matching).toHaveLength(expectedCount)
    expect(screen.getByText(matching[0].member_name)).toBeInTheDocument()
  })

  it('exports every parsed row regardless of the applied filter', async () => {
    renderApp('/dashboard', {
      filename: 'gainwell_271_redacted.edi',
      response: gainwellResponse,
    })

    fireEvent.change(screen.getByLabelText('Filter'), {
      target: { value: 'error' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Export Excel' }))

    await waitFor(() => {
      expect(exportEligibilityWorkbookMock).toHaveBeenCalledTimes(1)
    })

    const payload = exportEligibilityWorkbookMock.mock.calls[0][0] as {
      results: EligibilityResult[]
      parser_issue_count: number
    }
    expect(payload.results).toHaveLength(EXPECTED_TOTAL)
    expect(payload.parser_issue_count).toBe(0)
    expect(downloadBlobMock).toHaveBeenCalledTimes(1)
  })
})
