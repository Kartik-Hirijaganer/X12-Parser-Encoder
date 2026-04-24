import type { PatientValidationRow } from '../../types/api'
import { formatDate, formatStatusLabel, statusVariantFromValue } from '../../utils/formatters'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Table } from '../ui/Table'

export function PatientValidationTable({
  onSelect,
  rows,
}: {
  onSelect: (row: PatientValidationRow) => void
  rows: PatientValidationRow[]
}) {
  return (
    <Table
      columns={[
        {
          id: 'index',
          header: '#',
          cell: (row) => row.index + 1,
          sortValue: (row) => row.index,
        },
        {
          id: 'member_name',
          header: 'Member',
          cell: (row) => (
            <Button
              aria-label={`Open issues for ${row.member_name}`}
              className="min-h-0 px-0 py-0 text-left text-sm font-medium text-[var(--color-action-500)]"
              onClick={() => onSelect(row)}
              variant="quiet"
            >
              {row.member_name}
            </Button>
          ),
          sortValue: (row) => row.member_name,
        },
        {
          id: 'member_id',
          header: 'Member ID',
          cell: (row) => row.member_id ?? 'Not provided',
          sortValue: (row) => row.member_id ?? '',
        },
        {
          id: 'service_date',
          header: 'Service Date',
          cell: (row) => formatDate(row.service_date),
          sortValue: (row) => row.service_date ?? '',
        },
        {
          id: 'status',
          header: 'Status',
          cell: (row) => (
            <Badge variant={statusVariantFromValue(row.status)}>{formatStatusLabel(row.status)}</Badge>
          ),
          sortValue: (row) => row.status,
        },
        {
          id: 'errors',
          header: 'Errors',
          cell: (row) => row.error_count,
          sortValue: (row) => row.error_count,
        },
        {
          id: 'warnings',
          header: 'Warnings',
          cell: (row) => row.warning_count,
          sortValue: (row) => row.warning_count,
        },
      ]}
      emptyMessage="No patients match the current filter."
      pageSize={25}
      rowKey={(row) => `${row.index}-${row.transaction_control_number ?? row.member_id ?? row.member_name}`}
      rows={rows}
    />
  )
}
