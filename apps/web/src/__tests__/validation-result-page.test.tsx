import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ValidationResultPage } from '../pages/ValidationResultPage'
import { validateResponseFixture } from './fixtures'
import { renderWithProviders } from './testUtils'

describe('ValidationResultPage', () => {
  it('shows plain-English validation messages with suggestions', () => {
    renderWithProviders(<ValidationResultPage />, {
      route: '/validate/result',
      state: {
        filename: 'bad.270',
        response: validateResponseFixture,
      },
    })

    expect(screen.getByText("Row 12: Member ID '1234' is too short.")).toBeInTheDocument()
    expect(screen.getByText(/Suggested fix: Confirm the member ID and regenerate the file./)).toBeInTheDocument()
  })
})
