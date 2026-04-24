import type { EligibilityResult } from '../../types/api'
import { formatStatusLabel, statusVariantFromValue, summarizePlan } from '../../utils/formatters'
import { Badge } from '../ui/Badge'
import { Table } from '../ui/Table'
import { DashboardRow } from './DashboardRow'

export function DashboardTable({ results }: { results: EligibilityResult[] }) {
  return (
    <Table
      columns={[
        {
          id: 'index',
          header: '#',
          cell: (_, index) => index + 1,
          sortValue: () => 0,
        },
        {
          id: 'member_name',
          header: 'Name',
          cell: (result) => result.member_name,
          sortValue: (result) => result.member_name,
        },
        {
          id: 'member_id',
          header: 'Member ID',
          cell: (result) => result.member_id ?? 'Not returned',
          sortValue: (result) => result.member_id ?? '',
        },
        {
          id: 'status',
          header: 'Status',
          cell: (result) => (
            <Badge variant={statusVariantFromValue(result.overall_status)}>
              {formatStatusLabel(result.overall_status)}
            </Badge>
          ),
          sortValue: (result) => result.overall_status,
        },
        {
          id: 'plan',
          header: 'Plan',
          cell: (result) => summarizePlan(result),
          sortValue: (result) => summarizePlan(result),
        },
      ]}
      emptyMessage="No eligibility rows match the current filter."
      pageSize={8}
      renderExpandedRow={(result) => <DashboardRow result={result} />}
      rowKey={(result, index) =>
        result.st_control_number ??
        result.trace_number ??
        `${result.member_name}-${result.member_id ?? index}`
      }
      rows={results}
    />
  )
}
