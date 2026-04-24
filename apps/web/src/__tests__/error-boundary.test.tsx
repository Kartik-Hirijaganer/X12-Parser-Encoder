import { render, screen } from '@testing-library/react'
import type { ReactElement } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { ErrorBoundary } from '../components/ui/ErrorBoundary'

function Boom(): ReactElement {
  throw new Error('boom')
}

describe('ErrorBoundary', () => {
  it('renders children when no error is thrown', () => {
    render(
      <ErrorBoundary>
        <p>Healthy child</p>
      </ErrorBoundary>,
    )

    expect(screen.getByText('Healthy child')).toBeInTheDocument()
  })

  it('renders the fallback when a child throws', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reload page' })).toBeInTheDocument()

    spy.mockRestore()
  })

  it('invokes a custom fallback when provided', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary fallback={(reset) => <button onClick={reset}>Retry</button>}>
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()

    spy.mockRestore()
  })
})
