import { Button } from '../ui/Button'
import { DownloadIcon } from '../ui/Icons'
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
    <div className="space-y-4">
      <div className="flex justify-stretch sm:justify-end">
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
