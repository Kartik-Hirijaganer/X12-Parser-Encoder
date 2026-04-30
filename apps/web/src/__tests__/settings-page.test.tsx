import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SettingsPage } from '../pages/SettingsPage'
import { SETTINGS_STORAGE_KEY } from '../utils/constants'
import { renderWithProviders } from './testUtils'
import { configuredSettings } from './fixtures'

describe('SettingsPage', () => {
  it('renders all Phase 1 config groups', async () => {
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

    expect(screen.getByText('Interchange Control Number')).toBeInTheDocument()
    expect(screen.getByText('ICN is required before generation.')).toBeInTheDocument()
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

    fireEvent.change(screen.getByRole('textbox', { name: /Provider NPI/ }), {
      target: { value: '1234567890' },
    })
    expect(screen.getByText('Invalid NPI (Luhn check failed).')).toBeInTheDocument()

    fireEvent.change(screen.getByRole('combobox', { name: /Payer Profile/ }), {
      target: { value: 'dc_medicaid' },
    })

    await waitFor(() => {
      expect(screen.getByRole('textbox', { name: /Payer ID/ })).toHaveValue('DCMEDICAID')
      expect(screen.getByRole('textbox', { name: /Receiver ID \(ISA08\)/ })).toHaveValue(
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

    fireEvent.change(screen.getByRole('textbox', { name: /Organization Name/ }), {
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
      expect(screen.getByRole('textbox', { name: /Set your last submitted ICN/ })).toHaveValue(
        '000000041',
      )
    })
    expect(screen.getByDisplayValue('ACME HOME HEALTH')).toBeInTheDocument()
    expect(window.localStorage.getItem(SETTINGS_STORAGE_KEY)).not.toContain('ACME HOME HEALTH')
  })

  it('saves the ICN independently from provider settings', async () => {
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

    const input = screen.getByRole('textbox', { name: /Set your last submitted ICN/ })
    fireEvent.change(input, { target: { value: '19' } })
    fireEvent.blur(input)

    expect(input).toHaveValue('000000019')
    expect(screen.getByText('000000019')).toBeInTheDocument()
    expect(screen.getByText('000000020')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Save ICN' }))

    await waitFor(() => {
      expect(window.localStorage.getItem(SETTINGS_STORAGE_KEY)).toContain(
        '"lastIsaControlNumber":19',
      )
    })
  })

  it('does not persist field blur until Save Changes is clicked', async () => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(configuredSettings))

    renderWithProviders(<SettingsPage />, { route: '/settings' })

    const organization = screen.getByRole('textbox', { name: /Organization Name/ })
    fireEvent.change(organization, { target: { value: 'UPDATED ORG' } })
    fireEvent.blur(organization)

    expect(JSON.parse(window.localStorage.getItem(SETTINGS_STORAGE_KEY) ?? '{}')).toMatchObject({
      organizationName: configuredSettings.organizationName,
    })

    fireEvent.click(screen.getAllByRole('button', { name: 'Save Changes' })[0])

    await waitFor(() => {
      expect(JSON.parse(window.localStorage.getItem(SETTINGS_STORAGE_KEY) ?? '{}')).toMatchObject({
        organizationName: 'UPDATED ORG',
      })
    })
  })

  it('discards draft changes from the sticky unsaved bar', () => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(configuredSettings))

    renderWithProviders(<SettingsPage />, { route: '/settings' })

    const organization = screen.getByRole('textbox', { name: /Organization Name/ })
    fireEvent.change(organization, { target: { value: 'UPDATED ORG' } })

    expect(screen.getByText('You have unsaved settings changes.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Discard' }))

    expect(screen.getByRole('textbox', { name: /Organization Name/ })).toHaveValue(
      configuredSettings.organizationName,
    )
  })

  it('blocks Save Changes when inline validation fails', async () => {
    window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(configuredSettings))

    renderWithProviders(<SettingsPage />, { route: '/settings' })

    fireEvent.change(screen.getByRole('textbox', { name: /Payer ID/ }), {
      target: { value: '' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: 'Save Changes' })[0])

    expect(screen.getByText('Fix the highlighted settings fields before saving.')).toBeInTheDocument()
    expect(screen.getByText('Payer ID is required.')).toBeInTheDocument()

    await waitFor(() => {
      expect(JSON.parse(window.localStorage.getItem(SETTINGS_STORAGE_KEY) ?? '{}')).toMatchObject({
        payerId: configuredSettings.payerId,
      })
    })
  })
})
