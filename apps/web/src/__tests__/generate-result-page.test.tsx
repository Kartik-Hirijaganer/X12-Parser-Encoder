import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { generateResponseFixture } from './fixtures'
import { renderApp } from './testUtils'
import { Toaster } from '../components/ui/Toast'

describe('GenerateResultPage', () => {
  it('renders the generated submission filenames and batch summary', () => {
    renderApp('/generate/result', {
      filename: 'eligibility.csv',
      response: generateResponseFixture,
    })

    expect(screen.getByText('Submission package')).toBeInTheDocument()
    expect(screen.getByText('Batch summary')).toBeInTheDocument()
    expect(screen.getByText(generateResponseFixture.downloadFileName!)).toBeInTheDocument()
    expect(
      screen.getByText(generateResponseFixture.batchSummaryFileName!),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download Batch Summary' })).toBeEnabled()
  })

  it('copies the raw x12 payload to the clipboard and shows a success toast', async () => {
    const writeText = vi.mocked(navigator.clipboard.writeText)

    render(<Toaster />)
    renderApp('/generate/result', {
      filename: 'eligibility.csv',
      response: generateResponseFixture,
    })

    fireEvent.click(screen.getByRole('button', { name: 'Copy to Clipboard' }))

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(generateResponseFixture.x12Content)
    })
    await waitFor(() => {
      expect(screen.getByText('Copied X12 to clipboard')).toBeInTheDocument()
    })
  })
})
