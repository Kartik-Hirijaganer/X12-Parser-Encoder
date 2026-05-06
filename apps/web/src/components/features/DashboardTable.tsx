import type { EligibilityResult, PlanOption, PlanView } from '../../types/api'
import { formatStatusLabel, statusVariantFromValue } from '../../utils/formatters'
import { planBillingNote, selectedPlanOptions } from '../../utils/plan'
import { Badge } from '../ui/Badge'
import { EmptyState } from '../ui/EmptyState'
import { SearchIcon } from '../ui/Icons'
import { Table } from '../ui/Table'
import { DashboardRow } from './DashboardRow'

export function DashboardTable({
  planView,
  results,
}: {
  planView: PlanView
  results: EligibilityResult[]
}) {
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
          cell: (result) => (
            <PlanValueList
              options={planCell(result, planView)}
              valueForOption={(option) => option.programName}
            />
          ),
          sortValue: (result) => planSortValue(result, planView, 'programName'),
        },
        {
          id: 'payer_code',
          header: 'Payer Code',
          cell: (result) => (
            <PlanValueList
              className="font-mono"
              options={planCell(result, planView)}
              valueForOption={(option) => option.payerCode}
            />
          ),
          className: 'font-mono',
          sortValue: (result) => planSortValue(result, planView, 'payerCode'),
        },
        {
          id: 'category',
          header: 'Category',
          cell: (result) => {
            const options = planCell(result, planView)
            if (options.length === 0) {
              return 'Not returned'
            }
            return (
              <div className="flex min-w-32 flex-col items-start gap-1">
                {options.map((option) => {
                  const category = option.category || 'Not returned'
                  return (
                    <span key={planOptionKey(option)} title={planOptionTitle(option)}>
                      <Badge
                        variant={category.toUpperCase() === 'BUY-IN' ? 'warning' : 'notfound'}
                      >
                        {category}
                      </Badge>
                    </span>
                  )
                })}
              </div>
            )
          },
          sortValue: (result) => planSortValue(result, planView, 'category'),
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

function planCell(result: EligibilityResult, planView: PlanView): PlanOption[] {
  return selectedPlanOptions(result, planView)
}

function planSortValue(
  result: EligibilityResult,
  planView: PlanView,
  field: 'programName' | 'payerCode' | 'category',
): string {
  return planCell(result, planView)
    .map((option) => option[field])
    .filter(Boolean)
    .join(' | ')
}

function PlanValueList({
  className,
  options,
  valueForOption,
}: {
  className?: string
  options: PlanOption[]
  valueForOption: (option: PlanOption) => string
}) {
  if (options.length === 0) {
    return 'Not returned'
  }

  return (
    <div className="flex min-w-40 flex-col gap-1">
      {options.map((option) => (
        <span className={className} key={planOptionKey(option)} title={planOptionTitle(option)}>
          {valueForOption(option) || 'Not returned'}
        </span>
      ))}
    </div>
  )
}

function planOptionKey(option: PlanOption): string {
  return `${option.sourceSegmentIndex}-${option.label}-${option.programName}-${option.payerCode}`
}

function planOptionTitle(option: PlanOption): string {
  return [
    option.label,
    option.insuranceTypeCode ? `EB04 ${option.insuranceTypeCode}` : null,
    option.eligibilityCode ? `EB01 ${option.eligibilityCode}` : null,
    `segment ${option.sourceSegmentIndex + 1}`,
  ]
    .filter(Boolean)
    .join(' • ')
}
