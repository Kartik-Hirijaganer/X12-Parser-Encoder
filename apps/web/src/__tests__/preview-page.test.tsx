import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { PreviewPage } from '../pages/PreviewPage'
import { SETTINGS_STORAGE_KEY } from '../utils/constants'
import { configuredSettings, convertResponseFixture, generateResponseFixture } from './fixtures'
import { renderApp, renderWithProviders } from './testUtils'

describe('PreviewPage', () => {
  it('shows corrections as dismissible banners and partial-result warnings', () => {
    renderWithProviders(<PreviewPage />, {
      route: '/preview',
      state: {
        flow: 'generate',
        filename: 'eligibility.csv',
        response: convertResponseFixture,
      },
    })

    expect(screen.getByText('Uppercased the subscriber last name.')).toBeInTheDocument()
    expect(screen.getByText(/row had errors and were excluded/i)).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Dismiss'))
    expect(screen.queryByText('Uppercased the subscriber last name.')).not.toBeInTheDocument()
  })

  it('shows a confirmation prompt for short member IDs before generation', () => {
    renderWithProviders(<PreviewPage />, {
      route: '/preview',
      state: {
        flow: 'generate',
        filename: 'eligibility.csv',
        response: convertResponseFixture,
      },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Process' }))
    expect(screen.getByText('Some member IDs look shorter than expected.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue anyway' })).toBeInTheDocument()
  })

  it('records the highest generated ISA13 after a split generation response', async () => {
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        ...configuredSettings,
        lastIsaControlNumber: 41,
      }),
    )
    const splitResponse = {
      ...generateResponseFixture,
      x12_content: null,
      zip_content_base64: 'UEsDBAo=',
      split_count: 3,
      control_numbers: { isa13: '000000042', gs06: '42', st02_range: [] },
      archive_entries: [
        archiveEntry('000000042'),
        archiveEntry('000000044'),
        archiveEntry('000000043'),
      ],
    }
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => splitResponse,
    } as Response)

    renderApp('/preview', {
      flow: 'generate',
      filename: 'eligibility.csv',
      response: {
        ...convertResponseFixture,
        warnings: [],
        corrections: [],
        errors: [],
      },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Process' }))

    await waitFor(() => {
      const storedSettings = JSON.parse(
        window.localStorage.getItem(SETTINGS_STORAGE_KEY) ?? '{}',
      ) as typeof configuredSettings
      expect(storedSettings.lastIsaControlNumber).toBe(44)
    })

    const requestBody = JSON.parse(String(vi.mocked(fetch).mock.calls[0][1]?.body)) as {
      config: { isaControlNumberStart: number; gsControlNumberStart: number }
    }
    expect(requestBody.config.isaControlNumberStart).toBe(42)
    expect(requestBody.config.gsControlNumberStart).toBe(42)
  })
})

function archiveEntry(isa13: string) {
  return {
    file_name: `ACME123456_270_20260412_${isa13}.txt`,
    record_range_start: 1,
    record_range_end: 1,
    control_numbers: { isa13, gs06: String(Number(isa13)), st02_range: [] },
  }
}
