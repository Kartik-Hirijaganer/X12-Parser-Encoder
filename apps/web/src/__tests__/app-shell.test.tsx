import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { AppShell } from '../components/layout/AppShell'
import { renderWithProviders } from './testUtils'

describe('AppShell', () => {
  it('hides the icon-only Home link on the home route', () => {
    renderWithProviders(
      <AppShell title="Home">
        <div />
      </AppShell>,
      { route: '/' },
    )

    expect(screen.queryByRole('link', { name: 'Home' })).not.toBeInTheDocument()
  })

  it('shows an accessible icon-only Home link away from the home route', () => {
    renderWithProviders(
      <AppShell title="Settings">
        <div />
      </AppShell>,
      { route: '/settings' },
    )

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/')
  })
})
