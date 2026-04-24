import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SettingsPage } from '../pages/SettingsPage'
import { renderWithProviders } from './testUtils'
import { configuredSettings } from './fixtures'

describe('SettingsPage', () => {
  it('renders all four config groups', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          profiles: [
            {
              name: 'dc_medicaid',
              displayName: 'DC Medicaid',
              description: 'DC Medicaid eligibility profile.',
            },
          ],
        }),
      }),
    )

    renderWithProviders(<SettingsPage />, { route: '/settings' })

    expect(screen.getByText('Submitter / Provider Identity')).toBeInTheDocument()
    expect(screen.getByText('Payer / Receiver')).toBeInTheDocument()
    expect(screen.getByText('Envelope Defaults')).toBeInTheDocument()
    expect(screen.getByText('Transaction Defaults')).toBeInTheDocument()
  })

  it('shows live NPI validation and auto-fills payer defaults', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            profiles: [
              {
                name: 'dc_medicaid',
                displayName: 'DC Medicaid',
                description: 'DC Medicaid eligibility profile.',
              },
            ],
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            payerName: 'DC MEDICAID',
            payerId: 'DCMEDICAID',
            interchangeReceiverId: 'DCMEDICAID',
            receiverIdQualifier: 'ZZ',
            defaultServiceTypeCode: '30',
            maxBatchSize: 5000,
          }),
        }),
    )

    renderWithProviders(<SettingsPage />, { route: '/settings' })

    fireEvent.change(screen.getByRole('textbox', { name: /Provider NPI\*/ }), {
      target: { value: '1234567890' },
    })
    expect(screen.getByText('Invalid NPI (Luhn check failed).')).toBeInTheDocument()

    fireEvent.change(screen.getByRole('combobox', { name: /Payer Profile\*/ }), {
      target: { value: 'dc_medicaid' },
    })

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /Payer ID\*/ })).toHaveValue('DCMEDICAID')
      expect(screen.getByRole('textbox', { name: /Receiver ID \(ISA08\)\*/ })).toHaveValue(
        'DCMEDICAID',
      )
    })
  })

  it('exports and imports settings JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          profiles: [
            {
              name: 'dc_medicaid',
              displayName: 'DC Medicaid',
              description: 'DC Medicaid eligibility profile.',
            },
          ],
        }),
      }),
    )

    renderWithProviders(<SettingsPage />, { route: '/settings' })

    fireEvent.change(screen.getByRole('textbox', { name: /Organization Name\*/ }), {
      target: { value: configuredSettings.organizationName },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Export JSON' }))
    expect(URL.createObjectURL).toHaveBeenCalled()

    const file = new File([JSON.stringify(configuredSettings)], 'settings.json', {
      type: 'application/json',
    })
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByDisplayValue('ACME HOME HEALTH')).toBeInTheDocument()
    })
  })
})
