import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { UnsavedChangesBar } from '../components/ui/UnsavedChangesBar'

describe('UnsavedChangesBar', () => {
  it('renders Save and Discard actions', () => {
    const onDiscard = vi.fn()
    const onSave = vi.fn()

    render(<UnsavedChangesBar onDiscard={onDiscard} onSave={onSave} />)

    fireEvent.click(screen.getByRole('button', { name: 'Discard' }))
    fireEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    expect(onDiscard).toHaveBeenCalledOnce()
    expect(onSave).toHaveBeenCalledOnce()
  })
})
