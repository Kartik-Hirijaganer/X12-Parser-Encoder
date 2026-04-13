import type { ReactElement } from 'react'

import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import { AppRoutes } from '../App'
import { SettingsProvider } from '../hooks/useSettings'

export function renderWithProviders(
  ui: ReactElement,
  {
    route = '/',
    state,
  }: {
    route?: string
    state?: unknown
  } = {},
) {
  return render(
    <SettingsProvider>
      <MemoryRouter initialEntries={[state ? { pathname: route, state } : route]}>{ui}</MemoryRouter>
    </SettingsProvider>,
  )
}

export function renderApp(
  route = '/',
  state?: unknown,
) {
  return renderWithProviders(<AppRoutes />, { route, state })
}
