import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Button } from '../components/ui/Button'
import { Tooltip } from '../components/ui/Tooltip'

describe('Tooltip', () => {
  it('renders the trigger child as-is when idle', () => {
    render(
      <Tooltip content="More info">
        <Button>Hover target</Button>
      </Tooltip>,
    )

    expect(screen.getByRole('button', { name: 'Hover target' })).toBeInTheDocument()
  })
})
