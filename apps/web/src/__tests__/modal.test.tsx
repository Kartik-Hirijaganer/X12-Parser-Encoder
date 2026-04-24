import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'

import { Modal } from '../components/ui/Modal'

function Wrapper() {
  const [open, setOpen] = useState(true)
  return (
    <Modal description="A description" onOpenChange={setOpen} open={open} title="Demo">
      <p>Modal body</p>
    </Modal>
  )
}

describe('Modal', () => {
  it('renders the title, description, and body content', () => {
    render(<Wrapper />)

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Demo')).toBeInTheDocument()
    expect(screen.getByText('A description')).toBeInTheDocument()
    expect(screen.getByText('Modal body')).toBeInTheDocument()
  })

  it('closes on ESC', () => {
    render(<Wrapper />)

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    fireEvent.keyDown(document.body, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
