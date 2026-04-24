import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { DocumentIcon } from '../components/ui/Icons'

describe('EmptyState', () => {
  it('renders the title, description, icon, and action', () => {
    render(
      <EmptyState
        action={<Button>Upload</Button>}
        description="Upload a spreadsheet to get started."
        icon={<DocumentIcon data-testid="empty-icon" />}
        title="No rows yet"
      />,
    )

    expect(screen.getByText('No rows yet')).toBeInTheDocument()
    expect(screen.getByText('Upload a spreadsheet to get started.')).toBeInTheDocument()
    expect(screen.getByTestId('empty-icon')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument()
  })
})
