import { Button } from '../ui/Button'
import { DownloadIcon } from '../ui/Icons'
import { Select } from '../ui/Select'
import type { PlanView } from '../../types/api'
import { PLAN_VIEW_OPTIONS } from '../../utils/plan'
import { FilterBar } from './FilterBar'

const FILTER_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Inactive', value: 'inactive' },
  { label: 'Errors', value: 'error' },
  { label: 'Not Found', value: 'not_found' },
  { label: 'Unknown', value: 'unknown' },
] as const

export type DashboardStatusFilter = (typeof FILTER_OPTIONS)[number]['value']

export function DashboardFilterBar({
  filter,
  onExport,
  onFilterChange,
  onPlanViewChange,
  onSearchChange,
  planView,
  search,
}: {
  filter: DashboardStatusFilter
  onExport: () => void
  onFilterChange: (value: DashboardStatusFilter) => void
  onPlanViewChange: (value: PlanView) => void
  onSearchChange: (value: string) => void
  planView: PlanView
  search: string
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-text-primary)] sm:min-w-72">
          Plan view
          <Select
            onChange={(event) => onPlanViewChange(event.currentTarget.value as PlanView)}
            value={planView}
          >
            {PLAN_VIEW_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </label>
        <Button
          className="w-full sm:w-auto"
          leftIcon={<DownloadIcon className="h-4 w-4" />}
          onClick={onExport}
          variant="primary"
        >
          Export Excel
        </Button>
      </div>
      <FilterBar
        filter={filter}
        onFilterChange={onFilterChange}
        onSearchChange={onSearchChange}
        options={FILTER_OPTIONS}
        search={search}
        searchPlaceholder="Search member, ID, program, payer code, category, note, reason, or trace"
      />
    </div>
  )
}
