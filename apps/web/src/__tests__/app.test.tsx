import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from '../App'

describe('App', () => {
  it('renders the phase 0 scaffold shell', () => {
    render(<App />)

    expect(screen.getByText('X12 Eligibility Workbench')).toBeInTheDocument()
    expect(screen.getByText('Bootstrap checklist')).toBeInTheDocument()
  })
})
