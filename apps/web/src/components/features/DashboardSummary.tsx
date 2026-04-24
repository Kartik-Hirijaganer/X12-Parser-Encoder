import type { EligibilitySummary } from '../../types/api'
import { Card } from '../ui/Card'

type SummaryKey = 'active' | 'inactive' | 'error' | 'not_found' | 'unknown'
type SummaryVariant = 'active' | 'inactive' | 'warning' | 'notfound'

const SUMMARY_CARDS: Array<{
  key: SummaryKey
  label: string
  variant: SummaryVariant
}> = [
  { key: 'active', label: 'Active', variant: 'active' },
  { key: 'inactive', label: 'Inactive', variant: 'inactive' },
  { key: 'error', label: 'Errors', variant: 'warning' },
  { key: 'not_found', label: 'Not Found', variant: 'notfound' },
  { key: 'unknown', label: 'Unknown', variant: 'notfound' },
]

export function DashboardSummary({ summary }: { summary: EligibilitySummary }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
      {SUMMARY_CARDS.map((card) => (
        <Card className={`border ${cardClasses[card.variant]} p-5 shadow-none`} key={card.key}>
          <p className={`text-3xl font-semibold ${textClasses[card.variant]}`}>{summary[card.key]}</p>
          <p className="mt-2 text-sm font-medium text-[var(--color-text-primary)]">{card.label}</p>
        </Card>
      ))}
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
