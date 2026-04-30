import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SettingsProvider, useSettings } from '../hooks/useSettings'
import { configuredSettings } from './fixtures'
import { SETTINGS_STORAGE_KEY, MAX_ISA_CONTROL_NUMBER } from '../utils/constants'

function SettingsProbe() {
  const { hasUsableIcn, replaceSettings, settings } = useSettings()

  return (
    <div>
      <span>{settings.organizationName || 'missing'}</span>
      <span data-testid="icn-ready">{hasUsableIcn ? 'ready' : 'blocked'}</span>
      <button onClick={() => replaceSettings(configuredSettings)} type="button">
        Save
      </button>
    </div>
  )
}

function IcnTestProbe() {
  const { updateLastIcn, settings } = useSettings()

  return (
    <div>
      <span data-testid="icn-value">{settings.lastIsaControlNumber ?? 'null'}</span>
      <button onClick={() => updateLastIcn('000000042')} type="button">
        Update to 42
      </button>
      <button onClick={() => updateLastIcn('not-a-number')} type="button">
        Update invalid
      </button>
      <button onClick={() => updateLastIcn('42abc')} type="button">
        Update mixed
      </button>
      <button onClick={() => updateLastIcn('-1')} type="button">
        Update negative
      </button>
      <button onClick={() => updateLastIcn('0')} type="button">
        Update to 0 (out of range)
      </button>
      <button onClick={() => updateLastIcn(`${MAX_ISA_CONTROL_NUMBER + 1}`)} type="button">
        Update above max
      </button>
    </div>
  )
}

describe('useSettings', () => {
  it('reads and writes localStorage correctly', () => {
    render(
      <SettingsProvider>
        <SettingsProbe />
      </SettingsProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(screen.getByText('ACME HOME HEALTH')).toBeInTheDocument()
    expect(screen.getByTestId('icn-ready')).toHaveTextContent('ready')
    expect(window.localStorage.getItem(SETTINGS_STORAGE_KEY)).toContain('ACME HOME HEALTH')
  })

  it('updateLastIcn persists a valid ICN to localStorage', () => {
    render(
      <SettingsProvider>
        <IcnTestProbe />
      </SettingsProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Update to 42' }))

    expect(screen.getByTestId('icn-value')).toHaveTextContent('42')
    const stored = window.localStorage.getItem(SETTINGS_STORAGE_KEY)
    expect(stored).toContain('"lastIsaControlNumber":42')
  })

  it('updateLastIcn ignores non-numeric strings and does not corrupt state', () => {
    render(
      <SettingsProvider>
        <IcnTestProbe />
      </SettingsProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Update invalid' }))

    expect(screen.getByTestId('icn-value')).toHaveTextContent('null')

    fireEvent.click(screen.getByRole('button', { name: 'Update mixed' }))
    expect(screen.getByTestId('icn-value')).toHaveTextContent('null')
  })

  it('updateLastIcn ignores zero, negative, and values beyond 9 digits', () => {
    render(
      <SettingsProvider>
        <IcnTestProbe />
      </SettingsProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Update to 0 (out of range)' }))
    expect(screen.getByTestId('icn-value')).toHaveTextContent('null')

    fireEvent.click(screen.getByRole('button', { name: 'Update negative' }))
    expect(screen.getByTestId('icn-value')).toHaveTextContent('null')

    fireEvent.click(screen.getByRole('button', { name: 'Update above max' }))
    expect(screen.getByTestId('icn-value')).toHaveTextContent('null')
  })

  it('imported settings preserve a valid lastIsaControlNumber', () => {
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        ...configuredSettings,
        lastIsaControlNumber: 42,
      }),
    )

    render(
      <SettingsProvider>
        <IcnTestProbe />
      </SettingsProvider>,
    )

    expect(screen.getByTestId('icn-value')).toHaveTextContent('42')
  })

  it('sanitizeSettings clamps out-of-range lastIsaControlNumber to null', () => {
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        ...configuredSettings,
        lastIsaControlNumber: -1,
      }),
    )

    render(
      <SettingsProvider>
        <IcnTestProbe />
      </SettingsProvider>,
    )

    expect(screen.getByTestId('icn-value')).toHaveTextContent('null')
  })

  it('sanitizeSettings handles missing lastIsaControlNumber for data migration', () => {
    const withoutIcn: Partial<typeof configuredSettings> = { ...configuredSettings }
    delete withoutIcn.lastIsaControlNumber
    window.localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify(withoutIcn),
    )

    render(
      <SettingsProvider>
        <IcnTestProbe />
      </SettingsProvider>,
    )

    expect(screen.getByTestId('icn-value')).toHaveTextContent('null')
  })
})
