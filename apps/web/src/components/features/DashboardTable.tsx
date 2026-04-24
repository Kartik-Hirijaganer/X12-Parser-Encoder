import type { EligibilityResult } from '../../types/api'
import { formatStatusLabel, statusVariantFromValue, summarizePlan } from '../../utils/formatters'
import { Badge } from '../ui/Badge'
import { EmptyState } from '../ui/EmptyState'
import { SearchIcon } from '../ui/Icons'
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
          cell: (result) => result.memberName,
          sortValue: (result) => result.memberName,
        },
        {
          id: 'member_id',
          header: 'Member ID',
          cell: (result) => result.memberId ?? 'Not returned',
          sortValue: (result) => result.memberId ?? '',
        },
        {
          id: 'status',
          header: 'Status',
          cell: (result) => (
            <Badge variant={statusVariantFromValue(result.overallStatus)}>
              {formatStatusLabel(result.overallStatus)}
            </Badge>
          ),
          sortValue: (result) => result.overallStatus,
        },
        {
          id: 'plan',
          header: 'Plan',
          cell: (result) => summarizePlan(result),
          sortValue: (result) => summarizePlan(result),
        },
      ]}
      emptyMessage="No eligibility rows match the current filter."
      emptyState={
        <EmptyState
          className="border-0 bg-transparent py-6"
          description="Adjust the status filter to bring rows back into view."
          icon={<SearchIcon className="h-8 w-8" />}
          title="No matching eligibility rows"
        />
      }
      pageSize={8}
      renderExpandedRow={(result) => <DashboardRow result={result} />}
      rowKey={(result, index) =>
        result.stControlNumber ??
        result.traceNumber ??
        `${result.memberName}-${result.memberId ?? index}`
      }
      rows={results}
    />
  )
}
