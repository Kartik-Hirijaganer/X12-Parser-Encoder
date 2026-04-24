import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'

describe('form control primitives', () => {
  it('renders Input with label access and forwards changes', () => {
    const handleChange = vi.fn()

    render(
      <label>
        Search
        <Input onChange={handleChange} placeholder="Search rows" />
      </label>,
    )

    const input = screen.getByLabelText('Search')
    fireEvent.change(input, { target: { value: 'trace' } })

    expect(handleChange).toHaveBeenCalledTimes(1)
    expect(input.className).toContain('border-[var(--color-border-default)]')
  })

  it('renders Select with options and forwards changes', () => {
    const handleChange = vi.fn()

    render(
      <label>
        Filter
        <Select onChange={handleChange} value="all">
          <option value="all">All</option>
          <option value="active">Active</option>
        </Select>
      </label>,
    )

    const select = screen.getByLabelText('Filter')
    fireEvent.change(select, { target: { value: 'active' } })

    expect(handleChange).toHaveBeenCalledTimes(1)
    expect(select.className).toContain('appearance-none')
  })
})
