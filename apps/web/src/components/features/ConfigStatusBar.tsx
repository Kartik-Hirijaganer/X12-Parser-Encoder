import { useNavigate } from 'react-router-dom'

import { useSettings } from '../../hooks/useSettings'
import { cn } from '../../utils/cn'
import {
  formatIsaControlNumber,
  MAX_ISA_CONTROL_NUMBER,
  nextIsaControlNumber,
} from '../../utils/constants'
import { Button } from '../ui/Button'
import { WarningIcon } from '../ui/Icons'

export function ConfigStatusBar() {
  const navigate = useNavigate()
  const { hasRequiredSettings, hasUsableIcn, settings } = useSettings()
  const nextIcn = nextIsaControlNumber(settings.lastIsaControlNumber)
  const isReady = hasRequiredSettings && hasUsableIcn
  const statusMessage = getStatusMessage({
    hasRequiredSettings,
    lastIsaControlNumber: settings.lastIsaControlNumber,
    nextIcn,
  })

  return (
    <Button
      className={cn(
        '!w-full !justify-between !gap-3 !rounded-[var(--radius-lg)] border !px-4 !py-3 !text-left',
        isReady
          ? 'border-[var(--color-action-100)] bg-[var(--color-action-50)] text-[var(--color-text-primary)] hover:border-[var(--color-action-500)]'
          : 'border-[var(--color-warning-200)] bg-[var(--color-warning-50)] text-[var(--color-text-primary)] hover:border-[var(--color-warning-500)]',
      )}
      onClick={() => navigate('/settings')}
      variant="quiet"
    >
      <div className="flex min-w-0 items-center gap-3">
        {!isReady ? <WarningIcon className="h-5 w-5 text-[var(--color-warning-500)]" /> : null}
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">
            Provider: {settings.organizationName || 'Not configured'} | NPI:{' '}
            {settings.providerNpi || 'Not configured'} | Payer: {settings.payerName}
          </p>
          {!isReady ? (
            <p className="mt-1 text-caption text-[var(--color-warning-500)]">
              {statusMessage}
            </p>
          ) : (
            <p className="mt-1 text-caption text-[var(--color-action-500)]">{statusMessage}</p>
          )}
        </div>
      </div>
      <span className="shrink-0 rounded-[var(--radius-pill)] bg-[var(--color-surface-primary)] px-3 py-2 text-caption font-medium text-[var(--color-action-500)] shadow-[var(--shadow-sm)]">
        Settings
      </span>
    </Button>
  )
}

function getStatusMessage({
  hasRequiredSettings,
  lastIsaControlNumber,
  nextIcn,
}: {
  hasRequiredSettings: boolean
  lastIsaControlNumber: number | null
  nextIcn: number | null
}): string {
  if (!hasRequiredSettings) {
    return 'Provider settings incomplete.'
  }

  if (lastIsaControlNumber === null) {
    return 'ICN not set.'
  }

  if (lastIsaControlNumber === MAX_ISA_CONTROL_NUMBER) {
    return 'ICN exhausted at 999999999.'
  }

  return `Ready to generate. Next ICN ${formatIsaControlNumber(nextIcn ?? lastIsaControlNumber)}.`
}
