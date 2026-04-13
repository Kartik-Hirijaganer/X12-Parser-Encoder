import { fireEvent, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PreviewPage } from '../pages/PreviewPage'
import { convertResponseFixture } from './fixtures'
import { renderWithProviders } from './testUtils'

describe('PreviewPage', () => {
  it('shows corrections as dismissible banners and partial-result warnings', () => {
    renderWithProviders(<PreviewPage />, {
      route: '/preview',
      state: {
        flow: 'generate',
        filename: 'eligibility.csv',
        response: convertResponseFixture,
      },
    })

    expect(screen.getByText('Uppercased the subscriber last name.')).toBeInTheDocument()
    expect(screen.getByText(/row had errors and were excluded/i)).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Dismiss'))
    expect(screen.queryByText('Uppercased the subscriber last name.')).not.toBeInTheDocument()
  })

  it('shows a confirmation prompt for short member IDs before generation', () => {
    renderWithProviders(<PreviewPage />, {
      route: '/preview',
      state: {
        flow: 'generate',
        filename: 'eligibility.csv',
        response: convertResponseFixture,
      },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Process' }))
    expect(screen.getByText('Some member IDs look shorter than expected.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Continue anyway' })).toBeInTheDocument()
  })
})
