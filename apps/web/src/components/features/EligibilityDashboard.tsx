import { useDeferredValue, useMemo, useState } from 'react'

import type { EligibilityResult, EligibilitySummary } from '../../types/api'
import { Card } from '../ui/Card'
import { summarizePlan } from '../../utils/formatters'
import { DashboardFilterBar, type DashboardStatusFilter } from './DashboardFilterBar'
import { DashboardSummary } from './DashboardSummary'
import { DashboardTable } from './DashboardTable'

export function EligibilityDashboard({
  onExport,
  results,
  summary,
}: {
  onExport: () => void
  results: EligibilityResult[]
  summary: EligibilitySummary
}) {
  const [filter, setFilter] = useState<DashboardStatusFilter>('all')
  const [search, setSearch] = useState('')
  const deferredSearch = useDeferredValue(search)

  const filteredResults = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase()
    return results.filter((result) => {
      if (filter !== 'all' && result.overall_status !== filter) {
        return false
      }

      if (!normalizedSearch) {
        return true
      }

      return [
        result.member_name,
        result.member_id,
        summarizePlan(result),
        result.status_reason,
        result.trace_number,
      ]
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(normalizedSearch))
    })
  }, [deferredSearch, filter, results])

  return (
    <div className="space-y-6">
      <DashboardSummary summary={summary} />

      <Card className="space-y-4">
        <DashboardFilterBar
          filter={filter}
          onExport={onExport}
          onFilterChange={setFilter}
          onSearchChange={setSearch}
          search={search}
        />
        <DashboardTable results={filteredResults} />
      </Card>
    </div>
  )
}
