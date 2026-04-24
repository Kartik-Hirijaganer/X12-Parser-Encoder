import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { PatientValidationTable } from '../components/features/PatientValidationTable'
import type { PatientValidationRow } from '../types/api'

const fiveRows: PatientValidationRow[] = Array.from({ length: 5 }, (_unused, index) => ({
  index,
  transaction_control_number: String(index + 1).padStart(4, '0'),
  member_name: `MEMBER_${index + 1}`,
  member_id: `ID-${index + 1}`,
  service_date: '20260412',
  status: index === 1 ? 'invalid' : 'valid',
  error_count: index === 1 ? 2 : 0,
  warning_count: index === 1 ? 1 : 0,
  issues: [],
}))

describe('PatientValidationTable', () => {
  it('renders a Valid badge for valid rows and Invalid for invalid rows', () => {
    render(<PatientValidationTable onSelect={vi.fn()} rows={fiveRows} />)

    expect(screen.getAllByText('Valid')).toHaveLength(4)
    expect(screen.getAllByText('Invalid')).toHaveLength(1)
  })

  it('invokes onSelect when a member name is clicked', () => {
    const onSelect = vi.fn()
    render(<PatientValidationTable onSelect={onSelect} rows={fiveRows} />)

    fireEvent.click(screen.getByRole('button', { name: 'Open issues for MEMBER_2' }))

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith(fiveRows[1])
  })

  it('shows the empty state when no rows are provided', () => {
    render(<PatientValidationTable onSelect={vi.fn()} rows={[]} />)

    expect(screen.getByText('No patients match the current filter.')).toBeInTheDocument()
  })
})
