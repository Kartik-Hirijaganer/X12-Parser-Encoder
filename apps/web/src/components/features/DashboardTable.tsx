import type { EligibilityResult } from '../../types/api'
import { formatStatusLabel, statusVariantFromValue } from '../../utils/formatters'
import { planBillingNote, primaryPlanDescription, splitPlanDescription } from '../../utils/plan'
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
          id: 'program',
          header: 'Program',
          cell: (result) => planCell(result).programName || 'Not returned',
          sortValue: (result) => planCell(result).programName,
        },
        {
          id: 'payer_code',
          header: 'Payer Code',
          cell: (result) => planCell(result).payerCode || 'Not returned',
          className: 'font-mono',
          sortValue: (result) => planCell(result).payerCode,
        },
        {
          id: 'category',
          header: 'Category',
          cell: (result) => {
            const category = planCell(result).category
            if (!category) {
              return 'Not returned'
            }
            return (
              <Badge variant={category.toUpperCase() === 'BUY-IN' ? 'warning' : 'notfound'}>
                {category}
              </Badge>
            )
          },
          sortValue: (result) => planCell(result).category,
        },
        {
          id: 'notes',
          header: 'Notes',
          cell: (result) => planBillingNote(result) || 'Not returned',
          className: 'min-w-64',
          sortValue: (result) => planBillingNote(result),
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

function planCell(result: EligibilityResult) {
  return splitPlanDescription(primaryPlanDescription(result))
}
