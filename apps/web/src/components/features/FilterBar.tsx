import { startTransition } from 'react'

import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Select } from '../ui/Select'
import { cn } from '../../utils/cn'

export type FilterBarOption<TValue extends string> = {
  label: string
  value: TValue
}

export function FilterBar<TValue extends string>({
  actionLabel,
  className,
  filter,
  filterLabel = 'Filter',
  onAction,
  onFilterChange,
  onSearchChange,
  options,
  search,
  searchLabel = 'Search',
  searchPlaceholder,
}: {
  actionLabel?: string
  className?: string
  filter: TValue
  filterLabel?: string
  onAction?: () => void
  onFilterChange: (value: TValue) => void
  onSearchChange: (value: string) => void
  options: readonly FilterBarOption<TValue>[]
  search: string
  searchLabel?: string
  searchPlaceholder: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4',
        onAction ? 'lg:flex-row lg:items-center lg:justify-between' : 'sm:flex-row sm:items-center',
        className,
      )}
    >
      <div className="flex flex-1 flex-col gap-4 sm:flex-row sm:items-center">
        <label className="flex flex-col gap-2 text-sm font-medium text-[var(--color-text-primary)]">
          {filterLabel}
          <Select onChange={(event) => onFilterChange(event.currentTarget.value as TValue)} value={filter}>
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </label>
        <label className="flex min-w-72 flex-1 flex-col gap-2 text-sm font-medium text-[var(--color-text-primary)]">
          {searchLabel}
          <Input
            onChange={(event) => {
              const nextSearch = event.currentTarget.value
              startTransition(() => {
                onSearchChange(nextSearch)
              })
            }}
            placeholder={searchPlaceholder}
            value={search}
          />
        </label>
      </div>
      {onAction && actionLabel ? (
        <Button onClick={onAction} variant="primary">
          {actionLabel}
        </Button>
      ) : null}
    </div>
  )
}
