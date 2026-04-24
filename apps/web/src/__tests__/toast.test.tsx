import { render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Toaster, toast } from '../components/ui/Toast'

describe('Toast', () => {
  it('exposes only the sanctioned variant methods', () => {
    expect(typeof toast.success).toBe('function')
    expect(typeof toast.info).toBe('function')
    expect(typeof toast.warning).toBe('function')
    expect(typeof toast.error).toBe('function')
  })

  it('renders and announces a success toast via the Toaster surface', async () => {
    render(<Toaster />)

    toast.success('Saved successfully')

    await waitFor(() => {
      expect(screen.getByText('Saved successfully')).toBeInTheDocument()
    })
  })
})
