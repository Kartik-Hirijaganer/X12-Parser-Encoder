import type { EligibilitySummary } from '../../types/api'
import { cn } from '../../utils/cn'
import { Card } from '../ui/Card'
import type { DashboardStatusFilter } from './DashboardFilterBar'

type SummaryKey = 'error' | 'not_found' | 'unknown' | 'inactive' | 'active'
type SummaryVariant = 'warning' | 'notfound' | 'inactive' | 'active'

interface SummaryCardSpec {
  key: SummaryKey
  label: string
  variant: SummaryVariant
  filter: DashboardStatusFilter
}

const SUMMARY_CARDS: readonly SummaryCardSpec[] = [
  { key: 'error', label: 'Errors', variant: 'warning', filter: 'error' },
  { key: 'not_found', label: 'Not Found', variant: 'notfound', filter: 'not_found' },
  { key: 'unknown', label: 'Unknown', variant: 'notfound', filter: 'unknown' },
  { key: 'inactive', label: 'Inactive', variant: 'inactive', filter: 'inactive' },
  { key: 'active', label: 'Active', variant: 'active', filter: 'active' },
]

export function DashboardSummary({
  activeFilter,
  onFilterChange,
  summary,
}: {
  activeFilter: DashboardStatusFilter
  onFilterChange: (filter: DashboardStatusFilter) => void
  summary: EligibilitySummary
}) {
  return (
    <div
      aria-label="Eligibility status summary"
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
      role="group"
    >
      {SUMMARY_CARDS.map((card) => {
        const selected = activeFilter === card.filter
        const nextFilter: DashboardStatusFilter = selected ? 'all' : card.filter
        return (
          <Card
            aria-label={`Filter by ${card.label.toLowerCase()} — ${summary[card.key]} patients`}
            aria-pressed={selected}
            as="button"
            className={cn(
              'border p-5 shadow-none text-left transition-[background-color,border-color,transform] duration-[var(--duration-normal)] ease-[var(--ease-out)] hover:-translate-y-[var(--motion-lift-sm)]',
              cardClasses[card.variant],
              selected ? 'ring-[var(--focus-ring-width)] ring-[var(--color-focus-ring)]' : '',
            )}
            key={card.key}
            onClick={() => onFilterChange(nextFilter)}
            type="button"
          >
            <p className={`text-3xl font-semibold ${textClasses[card.variant]}`}>{summary[card.key]}</p>
            <p className="mt-2 text-sm font-medium text-[var(--color-text-primary)]">{card.label}</p>
          </Card>
        )
      })}
    </div>
  )
}

const cardClasses: Record<SummaryVariant, string> = {
  active: 'border-[var(--color-active-200)] bg-[var(--color-active-50)]',
  inactive: 'border-[var(--color-inactive-200)] bg-[var(--color-inactive-50)]',
  warning: 'border-[var(--color-warning-200)] bg-[var(--color-warning-50)]',
  notfound: 'border-[var(--color-notfound-200)] bg-[var(--color-notfound-50)]',
}

const textClasses: Record<SummaryVariant, string> = {
  active: 'text-[var(--color-active-500)]',
  inactive: 'text-[var(--color-inactive-500)]',
  warning: 'text-[var(--color-warning-500)]',
  notfound: 'text-[var(--color-notfound-500)]',
}
