import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { useApi } from '../hooks/useApi'

function ApiProbe({ requestFactory }: { requestFactory: () => Promise<string> }) {
  const { data, error, loading } = useApi(requestFactory, [])

  return (
    <div>
      <span>{loading ? 'loading' : 'idle'}</span>
      <span>{data ?? 'no-data'}</span>
      <span>{error?.message ?? 'no-error'}</span>
    </div>
  )
}

describe('useApi', () => {
  it('returns loading=true initially, then data', async () => {
    render(<ApiProbe requestFactory={() => Promise.resolve('done')} />)

    expect(screen.getByText('loading')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('done')).toBeInTheDocument()
      expect(screen.getByText('idle')).toBeInTheDocument()
    })
  })

  it('returns an error on reject', async () => {
    render(<ApiProbe requestFactory={() => Promise.reject(new Error('boom'))} />)

    await waitFor(() => {
      expect(screen.getByText('boom')).toBeInTheDocument()
    })
  })
})
