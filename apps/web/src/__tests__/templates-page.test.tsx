import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TemplatesPage } from '../pages/TemplatesPage'
import { renderWithProviders } from './testUtils'

describe('TemplatesPage', () => {
  it('renders download links for both templates', () => {
    renderWithProviders(<TemplatesPage />, { route: '/templates' })

    expect(screen.getByRole('link', { name: 'Download .xlsx' })).toHaveAttribute(
      'href',
      '/api/v1/templates/eligibility_template.xlsx',
    )
    expect(screen.getByRole('link', { name: 'Download .csv' })).toHaveAttribute(
      'href',
      '/api/v1/templates/eligibility_template.csv',
    )
  })
})
