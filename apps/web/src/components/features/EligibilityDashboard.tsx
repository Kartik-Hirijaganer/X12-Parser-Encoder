import { startTransition, useDeferredValue, useMemo, useState } from 'react'

import type { EligibilityResult, EligibilitySummary } from '../../types/api'
import { formatStatusLabel, statusVariantFromValue, summarizePlan } from '../../utils/formatters'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Table } from '../ui/Table'

const FILTER_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Inactive', value: 'inactive' },
  { label: 'Errors', value: 'error' },
  { label: 'Not Found', value: 'unknown' },
] as const

export function EligibilityDashboard({
  onExport,
  results,
  summary,
}: {
  onExport: () => void
  results: EligibilityResult[]
  summary: EligibilitySummary
}) {
  const [filter, setFilter] = useState<(typeof FILTER_OPTIONS)[number]['value']>('all')
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

      return [result.member_name, result.member_id, summarizePlan(result)]
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(normalizedSearch))
    })
  }, [deferredSearch, filter, results])

  const statCards = [
    { label: 'Active', value: summary.active, variant: 'active' as const },
    { label: 'Inactive', value: summary.inactive, variant: 'inactive' as const },
    { label: 'Errors', value: summary.error, variant: 'warning' as const },
    { label: 'Not Found', value: summary.unknown, variant: 'notfound' as const },
  ]

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => (
          <Card
            className={`border ${
              card.variant === 'active'
                ? 'border-[var(--color-active-200)] bg-[var(--color-active-50)]'
                : card.variant === 'inactive'
                  ? 'border-[var(--color-inactive-200)] bg-[var(--color-inactive-50)]'
                  : card.variant === 'warning'
                    ? 'border-[var(--color-warning-200)] bg-[var(--color-warning-50)]'
                    : 'border-[var(--color-notfound-200)] bg-[var(--color-notfound-50)]'
            } p-5 shadow-none`}
            key={card.label}
          >
            <p
              className={`text-[32px] font-semibold ${
                card.variant === 'active'
                  ? 'text-[var(--color-active-500)]'
                  : card.variant === 'inactive'
                    ? 'text-[var(--color-inactive-500)]'
                    : card.variant === 'warning'
                      ? 'text-[var(--color-warning-500)]'
                      : 'text-[var(--color-notfound-500)]'
              }`}
            >
              {card.value}
            </p>
            <p className="mt-2 text-[14px] font-medium text-[var(--color-text-primary)]">{card.label}</p>
          </Card>
        ))}
      </div>

      <Card className="space-y-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <label className="flex flex-col gap-2 text-[14px] font-medium text-[var(--color-text-primary)]">
              Filter
              <select
                className="min-h-11 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] px-3 py-2 text-[16px] text-[var(--color-text-primary)] focus:border-[var(--color-action-500)] focus:outline-none focus:ring-[3px] focus:ring-[var(--color-focus-ring)]"
                onChange={(event) => setFilter(event.currentTarget.value as typeof filter)}
                value={filter}
              >
                {FILTER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex min-w-[18rem] flex-1 flex-col gap-2 text-[14px] font-medium text-[var(--color-text-primary)]">
              Search
              <input
                className="min-h-11 rounded-[var(--radius-md)] border border-[var(--color-border-default)] bg-[var(--color-surface-primary)] px-3 py-2 text-[16px] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-action-500)] focus:outline-none focus:ring-[3px] focus:ring-[var(--color-focus-ring)]"
                onChange={(event) =>
                  startTransition(() => {
                    setSearch(event.currentTarget.value)
                  })
                }
                placeholder="Search member name, ID, or plan"
                value={search}
              />
            </label>
          </div>
          <Button onClick={onExport} variant="primary">
            Export Excel
          </Button>
        </div>

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
              cell: (result) => result.member_name,
              sortValue: (result) => result.member_name,
            },
            {
              id: 'member_id',
              header: 'Member ID',
              cell: (result) => result.member_id ?? 'Not returned',
              sortValue: (result) => result.member_id ?? '',
            },
            {
              id: 'status',
              header: 'Status',
              cell: (result) => (
                <Badge variant={statusVariantFromValue(result.overall_status)}>
                  {formatStatusLabel(result.overall_status)}
                </Badge>
              ),
              sortValue: (result) => result.overall_status,
            },
            {
              id: 'plan',
              header: 'Plan',
              cell: (result) => summarizePlan(result),
              sortValue: (result) => summarizePlan(result),
            },
          ]}
          emptyMessage="No eligibility rows match the current filter."
          pageSize={8}
          renderExpandedRow={(result) => (
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-2">
                <h4 className="text-[14px] font-semibold text-[var(--color-text-primary)]">
                  Eligibility Segments
                </h4>
                {result.eligibility_segments.length === 0 ? (
                  <p className="text-[14px] text-[var(--color-text-secondary)]">No eligibility segments returned.</p>
                ) : (
                  <ul className="space-y-2 text-[14px] text-[var(--color-text-primary)]">
                    {result.eligibility_segments.map((segment, index) => (
                      <li key={`${segment.eligibility_code}-${index}`}>
                        {segment.plan_coverage_description ?? 'Coverage returned'} • Code{' '}
                        {segment.eligibility_code}
                        {segment.service_type_code ? ` • Service ${segment.service_type_code}` : ''}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="space-y-2">
                <h4 className="text-[14px] font-semibold text-[var(--color-text-primary)]">Benefit Entities</h4>
                {result.benefit_entities.length === 0 ? (
                  <p className="text-[14px] text-[var(--color-text-secondary)]">No PCP or plan entity details returned.</p>
                ) : (
                  <ul className="space-y-2 text-[14px] text-[var(--color-text-primary)]">
                    {result.benefit_entities.map((entity, index) => (
                      <li key={`${entity.identifier}-${index}`}>
                        {entity.description ?? entity.qualifier ?? 'Entity'} • {entity.identifier}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="space-y-2">
                <h4 className="text-[14px] font-semibold text-[var(--color-text-primary)]">AAA Errors</h4>
                {result.aaa_errors.length === 0 ? (
                  <p className="text-[14px] text-[var(--color-text-secondary)]">No AAA errors returned.</p>
                ) : (
                  <ul className="space-y-2 text-[14px] text-[var(--color-text-primary)]">
                    {result.aaa_errors.map((error, index) => (
                      <li key={`${error.code}-${index}`}>
                        {error.message}
                        {error.suggestion ? (
                          <span className="text-[var(--color-text-secondary)]"> • {error.suggestion}</span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
          rowKey={(result, index) => `${result.member_name}-${result.member_id ?? index}`}
          rows={filteredResults}
        />
      </Card>
    </div>
  )
}
