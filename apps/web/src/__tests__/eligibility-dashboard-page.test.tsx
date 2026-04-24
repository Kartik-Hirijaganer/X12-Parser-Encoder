import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderApp } from './testUtils'
import { parseResponseFixture } from './fixtures'

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

describe('EligibilityDashboardPage', () => {
  beforeEach(() => {
    exportEligibilityWorkbookMock.mockReset()
    downloadBlobMock.mockReset()
    exportEligibilityWorkbookMock.mockResolvedValue(new Blob(['xlsx']))
  })

  it('does not render the parser issue banner when issue count is zero', () => {
    renderApp('/dashboard', {
      filename: 'response.271',
      response: parseResponseFixture,
    })

    expect(screen.queryByText('Parser Issues')).not.toBeInTheDocument()
  })

  it('renders a parser issue banner when issue count is non-zero', () => {
    renderApp('/dashboard', {
      filename: 'response.271',
      response: {
        ...parseResponseFixture,
        parserIssueCount: 2,
        parserIssues: [
          {
            transactionIndex: 1,
            transactionControlNumber: '0001',
            segmentId: 'EB',
            location: 'segment_position:12',
            message: 'Unexpected EB segment.',
            severity: 'error',
          },
          {
            transactionIndex: 2,
            transactionControlNumber: '0002',
            segmentId: 'NM1',
            location: 'segment_position:24',
            message: 'Unexpected NM1 segment.',
            severity: 'error',
          },
        ],
      },
    })

    expect(screen.getByText('Parser Issues')).toBeInTheDocument()
    expect(screen.getByText(/2 transaction\(s\) could not be fully parsed/)).toBeInTheDocument()
  })

  it('exports the full response payload after the table is filtered', async () => {
    renderApp('/dashboard', {
      filename: 'response.271',
      response: {
        ...parseResponseFixture,
        parserIssueCount: 1,
        parserIssues: [
          {
            transactionIndex: 5,
            transactionControlNumber: '0005',
            segmentId: 'PER',
            location: 'segment_position:48',
            message: 'Collected parser issue.',
            severity: 'error',
          },
        ],
      },
    })

    fireEvent.change(screen.getByLabelText('Filter'), {
      target: { value: 'active' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Export Excel' }))

    await waitFor(() => {
      expect(exportEligibilityWorkbookMock).toHaveBeenCalledTimes(1)
    })

    expect(exportEligibilityWorkbookMock).toHaveBeenCalledWith(
      expect.objectContaining({
        results: parseResponseFixture.results,
        parserIssueCount: 1,
        parserIssues: [
          expect.objectContaining({
            transactionControlNumber: '0005',
          }),
        ],
      }),
    )
    expect(downloadBlobMock).toHaveBeenCalledTimes(1)
  })
})
