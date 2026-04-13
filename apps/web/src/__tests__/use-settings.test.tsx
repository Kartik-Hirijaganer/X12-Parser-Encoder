import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SettingsProvider, useSettings } from '../hooks/useSettings'
import { configuredSettings } from './fixtures'
import { SETTINGS_STORAGE_KEY } from '../utils/constants'

function SettingsProbe() {
  const { replaceSettings, settings } = useSettings()

  return (
    <div>
      <span>{settings.organizationName || 'missing'}</span>
      <button onClick={() => replaceSettings(configuredSettings)} type="button">
        Save
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
    expect(window.localStorage.getItem(SETTINGS_STORAGE_KEY)).toContain('ACME HOME HEALTH')
  })
})
