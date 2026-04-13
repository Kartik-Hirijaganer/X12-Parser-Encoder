import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Table } from '../components/ui/Table'

const rows = [
  { id: '2', name: 'Bravo' },
  { id: '1', name: 'Alpha' },
  { id: '3', name: 'Charlie' },
]

describe('Table', () => {
  it('renders headers and rows, sorts on click, and paginates', () => {
    render(
      <Table
        columns={[
          {
            id: 'name',
            header: 'Name',
            cell: (row) => row.name,
            sortValue: (row) => row.name,
          },
        ]}
        pageSize={2}
        rowKey={(row) => row.id}
        rows={rows}
      />,
    )

    expect(screen.getByText('Bravo')).toBeInTheDocument()
    expect(screen.getByText('Alpha')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Name' }))

    const renderedRows = screen.getAllByRole('row')
    expect(renderedRows[1]).toHaveTextContent('Alpha')
    expect(renderedRows[2]).toHaveTextContent('Bravo')

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Charlie')).toBeInTheDocument()
  })
})
