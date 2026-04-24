import { Fragment, useMemo, useState } from 'react'

import { Button } from './Button'
import { ChevronRightIcon } from './Icons'
import { cn } from '../../utils/cn'

export interface TableColumn<T> {
  id: string
  header: string
  cell: (row: T, index: number) => React.ReactNode
  sortValue?: (row: T) => number | string
  className?: string
  headerClassName?: string
}

interface TableProps<T> {
  columns: Array<TableColumn<T>>
  emptyMessage?: string
  emptyState?: React.ReactNode
  pageSize?: number
  renderExpandedRow?: (row: T) => React.ReactNode
  rowKey: (row: T, index: number) => string
  rows: T[]
}

export function Table<T>({
  columns,
  emptyMessage = 'No rows to display.',
  emptyState,
  pageSize = 10,
  renderExpandedRow,
  rowKey,
  rows,
}: TableProps<T>) {
  const [sort, setSort] = useState<{ columnId: string; direction: 'asc' | 'desc' } | null>(null)
  const [page, setPage] = useState(0)
  const [expandedKeys, setExpandedKeys] = useState<Record<string, boolean>>({})

  const sortedRows = useMemo(() => {
    if (!sort) {
      return rows
    }

    const column = columns.find((entry) => entry.id === sort.columnId)
    if (!column?.sortValue) {
      return rows
    }

    return [...rows].sort((left, right) => {
      const leftValue = column.sortValue?.(left) ?? ''
      const rightValue = column.sortValue?.(right) ?? ''
      if (leftValue === rightValue) {
        return 0
      }
      const result = leftValue > rightValue ? 1 : -1
      return sort.direction === 'asc' ? result : -result
    })
  }, [columns, rows, sort])

  const totalPages = Math.max(1, Math.ceil(sortedRows.length / pageSize))
  const currentPage = Math.min(page, totalPages - 1)
  const visibleRows = sortedRows.slice(currentPage * pageSize, currentPage * pageSize + pageSize)

  return (
    <div className="overflow-hidden rounded-[var(--radius-xl)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)]">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          <thead className="bg-[var(--color-surface-tertiary)]">
            <tr>
              {renderExpandedRow ? <th className="w-12 px-4 py-3" /> : null}
              {columns.map((column) => (
                <th
                  className={cn(
                    'border-b-2 border-[var(--color-border-default)] px-4 py-3 text-left',
                    column.headerClassName,
                  )}
                  key={column.id}
                >
                  {column.sortValue ? (
                    <Button
                      onClick={() => {
                        setPage(0)
                        setSort((current) => {
                          if (!current || current.columnId !== column.id) {
                            return { columnId: column.id, direction: 'asc' }
                          }
                          if (current.direction === 'asc') {
                            return { columnId: column.id, direction: 'desc' }
                          }
                          return null
                        })
                      }}
                      variant="table"
                    >
                      {column.header}
                    </Button>
                  ) : (
                    <span className="text-caption font-semibold uppercase tracking-[0.04em] text-[var(--color-text-primary)]">
                      {column.header}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.length === 0 ? (
              <tr>
                <td
                  className="px-4 py-8 text-center text-sm text-[var(--color-text-secondary)]"
                  colSpan={columns.length + (renderExpandedRow ? 1 : 0)}
                >
                  {emptyState ?? emptyMessage}
                </td>
              </tr>
            ) : null}
            {visibleRows.map((row, index) => {
              const key = rowKey(row, index)
              const expanded = Boolean(expandedKeys[key])
              return (
                <Fragment key={key}>
                  <tr
                    className={cn(
                      'border-b border-[var(--color-border-subtle)] align-top odd:bg-[var(--color-surface-primary)] even:bg-[var(--color-row-alt)] hover:bg-[var(--color-surface-secondary)]',
                      expanded && 'bg-[var(--color-action-50)]',
                    )}
                  >
                    {renderExpandedRow ? (
                      <td className="px-4 py-3">
                        <Button
                          aria-label={expanded ? 'Collapse row' : 'Expand row'}
                          onClick={() =>
                            setExpandedKeys((current) => ({
                              ...current,
                              [key]: !current[key],
                            }))
                          }
                          size="icon"
                          variant="quiet"
                        >
                          <ChevronRightIcon
                            className={cn('h-4 w-4 transition-transform', expanded && 'rotate-90')}
                          />
                        </Button>
                      </td>
                    ) : null}
                    {columns.map((column) => (
                      <td
                        className={cn(
                          'px-4 py-3 text-sm leading-6 text-[var(--color-text-primary)]',
                          column.className,
                        )}
                        key={`${key}-${column.id}`}
                      >
                        {column.cell(row, currentPage * pageSize + index)}
                      </td>
                    ))}
                  </tr>
                  {expanded && renderExpandedRow ? (
                    <tr className="border-b border-[var(--color-border-subtle)] bg-[var(--color-action-50)]">
                      <td colSpan={columns.length + 1} className="px-4 py-4">
                        {renderExpandedRow(row)}
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
      {totalPages > 1 ? (
        <div className="flex items-center justify-between border-t border-[var(--color-border-subtle)] bg-[var(--color-surface-tertiary)] px-4 py-3">
          <p className="text-caption text-[var(--color-text-secondary)]">
            Page {currentPage + 1} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              disabled={currentPage === 0}
              onClick={() => setPage((value) => Math.max(0, value - 1))}
              size="sm"
              variant="secondary"
            >
              Previous
            </Button>
            <Button
              disabled={currentPage >= totalPages - 1}
              onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))}
              size="sm"
              variant="secondary"
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
