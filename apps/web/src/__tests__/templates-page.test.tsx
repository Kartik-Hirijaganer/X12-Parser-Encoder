import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TemplatesPage } from '../pages/TemplatesPage'
import { renderWithProviders } from './testUtils'

describe('TemplatesPage', () => {
  it('renders required columns first and download links second', () => {
    renderWithProviders(<TemplatesPage />, { route: '/templates' })

    const requiredColumns = screen.getByText('Required Columns')
    const excelTemplate = screen.getByText('Excel Template')
    expect(
      requiredColumns.compareDocumentPosition(excelTemplate) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Download .xlsx' })).toHaveAttribute(
      'href',
      '/api/v1/templates/eligibility_template.xlsx',
    )
    expect(screen.getByRole('link', { name: 'Download .csv' })).toHaveAttribute(
      'href',
      '/api/v1/templates/eligibility_template.csv',
    )
    expect(screen.getByRole('link', { name: 'Open Template Spec' })).toHaveAttribute(
      'href',
      '/api/v1/templates/template_spec.md',
    )
    expect(screen.queryByText('DC Medicaid Rules')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Next' })).not.toBeInTheDocument()
  })
})
