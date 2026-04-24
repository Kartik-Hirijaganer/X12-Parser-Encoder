import type { PatientValidationRow } from '../../types/api'
import { formatDate, formatStatusLabel, statusVariantFromValue } from '../../utils/formatters'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { IssueTable } from './IssueTable'

export function PatientIssueDrawer({
  onClose,
  row,
}: {
  onClose: () => void
  row: PatientValidationRow
}) {
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-xs uppercase text-[var(--color-text-tertiary)]">
            Patient #{row.index + 1}
          </p>
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
            {row.member_name}
          </h3>
          <p className="text-xs text-[var(--color-text-secondary)]">
            {row.member_id ? `Member ID ${row.member_id}` : 'Member ID not provided'}
            {row.service_date ? ` • Service ${formatDate(row.service_date)}` : ''}
            {row.transaction_control_number ? ` • ST ${row.transaction_control_number}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={statusVariantFromValue(row.status)}>{formatStatusLabel(row.status)}</Badge>
          <Button aria-label="Close issue drawer" onClick={onClose} size="sm" variant="secondary">
            Close
          </Button>
        </div>
      </div>
      <IssueTable issues={row.issues} />
    </Card>
  )
}
