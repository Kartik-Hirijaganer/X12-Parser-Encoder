import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { FileUpload } from '../components/ui/FileUpload'

describe('FileUpload', () => {
  it('renders a drop zone and fires onFileSelect on drop', () => {
    const onFileSelect = vi.fn()
    render(<FileUpload onFileSelect={onFileSelect} />)

    const dropZone = screen.getByRole('button', { name: /drag & drop any file here/i })
    const file = new File(['last_name,first_name'], 'eligibility.csv', { type: 'text/csv' })

    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [file],
      },
    })

    expect(onFileSelect).toHaveBeenCalledWith(file)
  })
})
