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
  onSearchChange,
  search,
}: {
  filter: DashboardStatusFilter
  onExport: () => void
  onFilterChange: (value: DashboardStatusFilter) => void
  onSearchChange: (value: string) => void
  search: string
}) {
  return (
    <FilterBar
      actionLabel="Export Excel"
      filter={filter}
      onAction={onExport}
      onFilterChange={onFilterChange}
      onSearchChange={onSearchChange}
      options={FILTER_OPTIONS}
      search={search}
      searchPlaceholder="Search member, ID, plan, reason, or trace"
    />
  )
}
