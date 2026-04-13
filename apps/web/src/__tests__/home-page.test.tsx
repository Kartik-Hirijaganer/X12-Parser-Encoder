import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { renderApp } from './testUtils'
import { configuredSettings, convertResponseFixture } from './fixtures'
import { SETTINGS_STORAGE_KEY } from '../utils/constants'

describe('HomePage', () => {
  it('renders three action cards and the drop zone', () => {
    renderApp('/')

    expect(screen.getByText('Generate 270')).toBeInTheDocument()
    expect(screen.getByText('Validate 270')).toBeInTheDocument()
    expect(screen.getByText('Parse 271')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /drag & drop any file here/i })).toBeInTheDocument()
  })

  it('shows config status details and disables generate when required settings are missing', () => {
    renderApp('/')

    expect(screen.getByText(/Provider: Not configured/)).toBeInTheDocument()
    expect(screen.getByText('Configure your provider details in Settings first.')).toBeInTheDocument()
  })

  it('routes a spreadsheet upload to the preview page', async () => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(configuredSettings))
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => convertResponseFixture,
      }),
    )

    renderApp('/')

    const file = new File(
      ['last_name,first_name,date_of_birth,gender,member_id,service_date\nSmith,John,19850115,M,12345678,20260412'],
      'eligibility.csv',
      { type: 'text/csv' },
    )

    fireEvent.drop(screen.getByRole('button', { name: /drag & drop any file here/i }), {
      dataTransfer: {
        files: [file],
      },
    })

    await waitFor(() => {
      expect(screen.getByText('Preview')).toBeInTheDocument()
      expect(screen.getByText('First five rows')).toBeInTheDocument()
    })

    expect(window.localStorage.getItem(SETTINGS_STORAGE_KEY)).toContain('ACME HOME HEALTH')
  })
})
