import { useDeferredValue, useMemo, useState } from 'react'

import type { EligibilityResult, EligibilitySummary, PlanOption, PlanView } from '../../types/api'
import { Card } from '../ui/Card'
import { EmptyState } from '../ui/EmptyState'
import { SearchIcon } from '../ui/Icons'
import { planBillingNote, planOptionsForResult, selectedPlanOptions } from '../../utils/plan'
import { DashboardFilterBar, type DashboardStatusFilter } from './DashboardFilterBar'
import { DashboardSummary } from './DashboardSummary'
import { DashboardTable } from './DashboardTable'

export function EligibilityDashboard({
  onExport,
  results,
  summary,
}: {
  onExport: (planView: PlanView) => void
  results: EligibilityResult[]
  summary: EligibilitySummary
}) {
  const [filter, setFilter] = useState<DashboardStatusFilter>('all')
  const [planView, setPlanView] = useState<PlanView>('all')
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)

  const filteredResults = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase()
    return results.filter((result) => {
      if (filter !== 'all' && result.overallStatus !== filter) {
        return false
      }

      if (!normalizedSearch) {
        return true
      }

      const selectedPlans = selectedPlanOptions(result, planView)
      const allPlans = planOptionsForResult(result)
      const billingNote = planBillingNote(result)

      return [
        result.memberName,
        result.memberId,
        ...searchablePlanFields(selectedPlans),
        ...searchablePlanFields(allPlans),
        billingNote,
        result.statusReason,
        result.traceNumber,
      ]
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(normalizedSearch))
    })
  }, [deferredSearch, filter, planView, results])

  const hasNoRows = results.length === 0

  return (
    <div className="space-y-6">
      <DashboardSummary activeFilter={filter} onFilterChange={setFilter} summary={summary} />

      {hasNoRows ? (
        <Card>
          <EmptyState
            description="The 271 response did not contain any eligibility rows. Upload another file to review results."
            icon={<SearchIcon className="h-10 w-10" />}
            title="No eligibility rows yet"
          />
        </Card>
      ) : (
        <Card className="space-y-4">
          <DashboardFilterBar
            filter={filter}
            onExport={() => onExport(planView)}
            onFilterChange={setFilter}
            onPlanViewChange={setPlanView}
            onSearchChange={setSearch}
            planView={planView}
            search={search}
          />
          <DashboardTable planView={planView} results={filteredResults} />
        </Card>
      )}
    </div>
  )
}

function searchablePlanFields(options: PlanOption[]): Array<string | null> {
  return options.flatMap((option) => [
    option.label,
    option.programName,
    option.payerCode,
    option.category,
    option.insuranceTypeCode,
    option.eligibilityCode,
  ])
}
