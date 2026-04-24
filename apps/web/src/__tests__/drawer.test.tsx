import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Drawer } from '../components/ui/Drawer'

describe('Drawer', () => {
  it('renders the drawer content with a title and close button', () => {
    render(
      <Drawer onOpenChange={() => {}} open title="Filters">
        <p>Filter options</p>
      </Drawer>,
    )

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Filters')).toBeInTheDocument()
    expect(screen.getByText('Filter options')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close drawer' })).toBeInTheDocument()
  })

  it('does not render content when closed', () => {
    render(
      <Drawer onOpenChange={() => {}} open={false} title="Filters">
        <p>Hidden</p>
      </Drawer>,
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
