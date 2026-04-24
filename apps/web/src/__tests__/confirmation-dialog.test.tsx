import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { Button } from '../components/ui/Button'
import { ConfirmationDialog } from '../components/ui/ConfirmationDialog'

function Harness({
  destructive = false,
  onConfirm = vi.fn(),
  onCancel = vi.fn(),
}: {
  destructive?: boolean
  onConfirm?: () => void
  onCancel?: () => void
}) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button onClick={() => setOpen(true)}>Open</Button>
      <ConfirmationDialog
        confirmLabel="Delete"
        description="This cannot be undone."
        destructive={destructive}
        onCancel={onCancel}
        onConfirm={onConfirm}
        onOpenChange={setOpen}
        open={open}
        title="Delete this record?"
      />
    </>
  )
}

describe('ConfirmationDialog', () => {
  it('invokes onConfirm when confirm is clicked', () => {
    const onConfirm = vi.fn()

    render(<Harness onConfirm={onConfirm} />)

    fireEvent.click(screen.getByRole('button', { name: 'Open' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('invokes onCancel when cancel is clicked', () => {
    const onCancel = vi.fn()

    render(<Harness onCancel={onCancel} />)

    fireEvent.click(screen.getByRole('button', { name: 'Open' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('applies destructive styling to the confirm button when destructive', () => {
    render(<Harness destructive />)

    fireEvent.click(screen.getByRole('button', { name: 'Open' }))
    const confirm = screen.getByRole('button', { name: 'Delete' })
    expect(confirm.className).toContain('bg-[var(--color-inactive-500)]')
  })
})
