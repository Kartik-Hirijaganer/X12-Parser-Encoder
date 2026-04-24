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
              aria-label={`Open issues for ${row.memberName}`}
              className="min-h-0 px-0 py-0 text-left text-sm font-medium text-[var(--color-action-500)]"
              onClick={() => onSelect(row)}
              variant="quiet"
            >
              {row.memberName}
            </Button>
          ),
          sortValue: (row) => row.memberName,
        },
        {
          id: 'member_id',
          header: 'Member ID',
          cell: (row) => row.memberId ?? 'Not provided',
          sortValue: (row) => row.memberId ?? '',
        },
        {
          id: 'service_date',
          header: 'Service Date',
          cell: (row) => formatDate(row.serviceDate),
          sortValue: (row) => row.serviceDate ?? '',
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
          cell: (row) => row.errorCount,
          sortValue: (row) => row.errorCount,
        },
        {
          id: 'warnings',
          header: 'Warnings',
          cell: (row) => row.warningCount,
          sortValue: (row) => row.warningCount,
        },
      ]}
      emptyMessage="No patients match the current filter."
      pageSize={25}
      rowKey={(row) => `${row.index}-${row.transactionControlNumber ?? row.memberId ?? row.memberName}`}
      rows={rows}
    />
  )
}
