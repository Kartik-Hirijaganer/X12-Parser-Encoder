import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderApp } from './testUtils'
import type { ValidateResponse } from '../types/api'

const exportValidationWorkbookMock = vi.hoisted(() => vi.fn())
const downloadBlobMock = vi.hoisted(() => vi.fn())
const downloadTextFileMock = vi.hoisted(() => vi.fn())

vi.mock('../services/api', () => ({
  ApiError: class ApiError extends Error {
    status = 500
    suggestion = null
  },
  exportValidationWorkbook: exportValidationWorkbookMock,
}))

vi.mock('../utils/downloads', () => ({
  downloadBlob: downloadBlobMock,
  downloadTextFile: downloadTextFileMock,
}))

function buildFiveRowResponse(overrides: Partial<ValidateResponse> = {}): ValidateResponse {
  const invalidIndex = 2
  const patients = Array.from({ length: 5 }, (_unused, index) => ({
    index,
    transactionControlNumber: String(index + 1).padStart(4, '0'),
    memberName: `MEMBER_${index + 1}`,
    memberId: `ID-${index + 1}`,
    serviceDate: '20260412',
    status: index === invalidIndex ? ('invalid' as const) : ('valid' as const),
    errorCount: index === invalidIndex ? 1 : 0,
    warningCount: 0,
    issues:
      index === invalidIndex
        ? [
            {
              severity: 'error',
              level: 'snip_2',
              code: 'E201',
              message: 'Member ID is too short.',
              location: 'segment_position:14',
              segmentId: 'NM1',
              element: 'NM109',
              suggestion: 'Confirm the member ID.',
              profile: 'dc_medicaid',
            },
          ]
        : [],
  }))

  return {
    filename: 'sample.270',
    isValid: false,
    errorCount: 1,
    warningCount: 0,
    issues: patients[invalidIndex]?.issues ?? [],
    patients,
    summary: {
      totalPatients: 5,
      validPatients: 4,
      invalidPatients: 1,
    },
    ...overrides,
  }
}

function expandFailureDetails() {
  fireEvent.click(screen.getByRole('button', { name: 'Show details' }))
}

describe('ValidationResultPage', () => {
  beforeEach(() => {
    exportValidationWorkbookMock.mockReset()
    downloadBlobMock.mockReset()
    downloadTextFileMock.mockReset()
    exportValidationWorkbookMock.mockResolvedValue(new Blob(['xlsx']))
  })

  it('renders header metrics for Total / Valid / Invalid', () => {
    renderApp('/validate/result', {
      filename: 'sample.270',
      response: buildFiveRowResponse(),
    })

    const totalMetric = screen.getByText('Total').closest('div')
    expect(totalMetric).toHaveTextContent('5')
    const validMetric = screen.getAllByText('Valid')[0].closest('div')
    expect(validMetric).toHaveTextContent('4')
    const invalidMetric = screen.getAllByText('Invalid')[0].closest('div')
    expect(invalidMetric).toHaveTextContent('1')
  })

  it('narrows the patient table when the Invalid filter is selected', () => {
    renderApp('/validate/result', {
      filename: 'sample.270',
      response: buildFiveRowResponse(),
    })

    expandFailureDetails()
    fireEvent.change(screen.getByLabelText('Filter'), { target: { value: 'invalid' } })

    expect(screen.getByText('MEMBER_3')).toBeInTheDocument()
    expect(screen.queryByText('MEMBER_1')).not.toBeInTheDocument()
  })

  it('opens the drawer with issue detail when a row is clicked', () => {
    renderApp('/validate/result', {
      filename: 'sample.270',
      response: buildFiveRowResponse(),
    })

    expandFailureDetails()
    fireEvent.click(screen.getByRole('button', { name: 'Open issues for MEMBER_3' }))

    expect(screen.getByText('Patient #3')).toBeInTheDocument()
    expect(screen.getByText('Member ID is too short.')).toBeInTheDocument()
  })

  it('posts the full response payload when Export Excel is clicked', async () => {
    const response = buildFiveRowResponse()
    renderApp('/validate/result', {
      filename: 'sample.270',
      response,
    })

    fireEvent.click(screen.getAllByRole('button', { name: 'Export Excel' })[0])

    await waitFor(() => {
      expect(exportValidationWorkbookMock).toHaveBeenCalledTimes(1)
    })
    expect(exportValidationWorkbookMock).toHaveBeenCalledWith(response)
    expect(downloadBlobMock).toHaveBeenCalledTimes(1)
  })

  it('shows a success banner and one-sentence failure summary', () => {
    renderApp('/validate/result', {
      filename: 'sample.270',
      response: buildFiveRowResponse(),
    })

    expect(screen.getByText('Validation failed')).toBeInTheDocument()
    expect(screen.getByText(/1 critical issue/)).toBeInTheDocument()

    renderApp('/validate/result', {
      filename: 'sample.270',
      response: buildFiveRowResponse({
        isValid: true,
        errorCount: 0,
        warningCount: 0,
        issues: [],
        patients: [],
        summary: { totalPatients: 0, validPatients: 0, invalidPatients: 0 },
      }),
    })

    expect(screen.getByText('All patients validated successfully')).toBeInTheDocument()
  })
})
