import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import type { WarningMessage } from '../types/api'
import type { PreviewRouteState } from '../types/workflow'
import { useSettings } from '../hooks/useSettings'
import { ApiError, ApiTimeoutError, generate270, parse271, validate270 } from '../services/api'
import { highestIsa13, nextIsaControlNumber } from '../utils/constants'
import { formatBytes, formatDate } from '../utils/formatters'
import { AppShell } from '../components/layout/AppShell'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ProgressBar } from '../components/ui/ProgressBar'
import { Skeleton } from '../components/ui/Skeleton'
import { Table } from '../components/ui/Table'

export function PreviewPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { settings, updateLastIcn } = useSettings()
  const routeState = location.state as PreviewRouteState | null
  const [dismissedCorrectionIndexes, setDismissedCorrectionIndexes] = useState<Record<number, boolean>>({})
  const [showRowErrorDetails, setShowRowErrorDetails] = useState(false)
  const [pendingMemberIdConfirmation, setPendingMemberIdConfirmation] = useState(false)
  const [processingLabel, setProcessingLabel] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [timeout, setTimeout] = useState<{ retry: () => void } | null>(null)

  if (!routeState) {
    return (
      <AppShell title="Preview unavailable">
        <Card className="space-y-4">
          <p className="text-base text-[var(--color-text-secondary)]">
            Start from the home page to preview a file before processing it.
          </p>
          <Button onClick={() => navigate('/')} variant="primary">
            Go Home
          </Button>
        </Card>
      </AppShell>
    )
  }

  const previewState = routeState
  const memberIdWarnings =
    previewState.flow === 'generate'
      ? previewState.response.warnings.filter(isMemberIdWarning)
      : []

  async function handleProcess(forceMemberIdConfirmation = false) {
    const run = async () => {
      setError(null)
      setTimeout(null)

      try {
        if (previewState.flow === 'generate') {
          setProcessingLabel(`Generating X12 file for ${previewState.response.record_count} records...`)
          const nextIcn = nextIsaControlNumber(settings.lastIsaControlNumber)
          const response = await generate270(settings, previewState.response.patients, nextIcn)
          navigate('/generate/result', {
            state: {
              filename: previewState.filename,
              response,
            },
          })
          const highestIcn = highestIsa13(response)
          if (highestIcn !== null) {
            updateLastIcn(highestIcn.toString().padStart(9, '0'))
          }
          return
        }

        if (previewState.flow === 'validate') {
          setProcessingLabel('Validating X12 file...')
          const response = await validate270(
            new File([previewState.rawText], previewState.filename, { type: 'text/plain' }),
            settings.payerProfile,
          )
          navigate('/validate/result', {
            state: {
              filename: previewState.filename,
              response,
            },
          })
          return
        }

        setProcessingLabel('Parsing 271 response...')
        const response = await parse271(
          new File([previewState.rawText], previewState.filename, { type: 'text/plain' }),
        )
        navigate('/dashboard', {
          state: {
            filename: previewState.filename,
            response,
          },
        })
      } catch (caughtError) {
        if (caughtError instanceof ApiTimeoutError) {
          setTimeout({ retry: () => void run() })
          return
        }

        if (caughtError instanceof ApiError) {
          setError(caughtError.suggestion ? `${caughtError.message} Suggested fix: ${caughtError.suggestion}` : caughtError.message)
          return
        }

        setError(caughtError instanceof Error ? caughtError.message : 'The request failed.')
      } finally {
        setProcessingLabel(null)
      }
    }

    if (
      previewState.flow === 'generate' &&
      memberIdWarnings.length > 0 &&
      !forceMemberIdConfirmation
    ) {
      setPendingMemberIdConfirmation(true)
      return
    }

    await run()
  }

  const rowCount =
    previewState.flow === 'generate'
      ? previewState.response.record_count
      : previewState.preview.subscriberNames.length
  const rowLabel =
    previewState.flow === 'generate'
      ? `${rowCount} ${rowCount === 1 ? 'row' : 'rows'}`
      : `${rowCount} ${rowCount === 1 ? 'subscriber' : 'subscribers'}`
  const isProcessing = processingLabel !== null

  return (
    <AppShell
      subtitle="Review the file summary before sending it to the backend. Corrections and excluded rows are shown here so the operator can decide whether to continue."
      title="Preview"
    >
      <Card className="flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <p className="text-caption font-medium uppercase tracking-[0.04em] text-[var(--color-text-tertiary)]">
            File
          </p>
          <p className="truncate text-base font-semibold text-[var(--color-text-primary)]">
            {previewState.filename}
          </p>
          <p className="text-caption text-[var(--color-text-secondary)]">
            {previewState.fileSize !== undefined ? formatBytes(previewState.fileSize) : 'Size unknown'}
            {' • '}
            {rowLabel}
          </p>
        </div>
      </Card>

      {previewState.flow === 'generate'
        ? previewState.response.corrections.map((correction, index) =>
            dismissedCorrectionIndexes[index] ? null : (
              <Banner
                key={`${correction.row}-${correction.field}-${index}`}
                onDismiss={() =>
                  setDismissedCorrectionIndexes((current) => ({
                    ...current,
                    [index]: true,
                  }))
                }
                title={`Row ${correction.row}: ${correction.field}`}
                variant="warning"
              >
                {correction.message}
              </Banner>
            ),
          )
        : null}

      {previewState.flow === 'generate' && previewState.response.errors.length > 0 ? (
        <Banner
          actions={
            <Button
              onClick={() => setShowRowErrorDetails((current) => !current)}
              size="sm"
              variant="secondary"
            >
              {showRowErrorDetails ? 'Hide details' : 'Show details'}
            </Button>
          }
          title={`${previewState.response.errors.length} row${previewState.response.errors.length === 1 ? '' : 's'} had errors and were excluded.`}
          variant="warning"
        >
          You can continue with the valid rows or fix the source file and upload it again.
        </Banner>
      ) : null}

      {pendingMemberIdConfirmation ? (
        <Banner
          actions={
            <>
              <Button
                onClick={() => {
                  setPendingMemberIdConfirmation(false)
                  void handleProcess(true)
                }}
                size="sm"
                variant="primary"
              >
                Continue anyway
              </Button>
              <Button
                onClick={() => setPendingMemberIdConfirmation(false)}
                size="sm"
                variant="secondary"
              >
                Review rows again
              </Button>
            </>
          }
          title="Some member IDs look shorter than expected."
          variant="warning"
        >
          The preview kept those rows unchanged. Confirm before generating the 270 output.
        </Banner>
      ) : null}

      {error ? <Banner variant="error">{error}</Banner> : null}

      {timeout ? (
        <Banner
          actions={
            <>
              <Button onClick={timeout.retry} size="sm" variant="primary">
                Retry
              </Button>
              <Button onClick={() => setTimeout(null)} size="sm" variant="secondary">
                Cancel
              </Button>
            </>
          }
          title="Request timed out"
          variant="warning"
        >
          Processing is taking longer than expected. This may happen with very large files.
        </Banner>
      ) : null}

      {processingLabel ? (
        <Card className="space-y-3">
          <p className="text-sm text-[var(--color-text-secondary)]">{processingLabel}</p>
          <ProgressBar label={processingLabel} variant="indeterminate" />
        </Card>
      ) : null}

      {isProcessing ? (
        <Card className="space-y-3">
          <Skeleton aria-label="Loading summary row" height="1.5rem" width="30%" />
          <Skeleton aria-label="Loading table row" height="1rem" />
          <Skeleton aria-label="Loading table row" height="1rem" />
          <Skeleton aria-label="Loading table row" height="1rem" />
          <Skeleton aria-label="Loading table row" height="1rem" />
        </Card>
      ) : previewState.flow === 'generate' ? (
        <div className="space-y-6">
          <Card className="grid gap-4 md:grid-cols-4">
            <SummaryCard label="Rows ready" value={String(previewState.response.record_count)} />
            <SummaryCard label="Warnings" value={String(previewState.response.warnings.length)} />
            <SummaryCard label="Corrections" value={String(previewState.response.corrections.length)} />
            <SummaryCard label="Excluded rows" value={String(previewState.response.errors.length)} />
          </Card>

          <Card className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">First five rows</h2>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                Provider and payer identity come from Settings, not the template itself.
              </p>
            </div>
            <Table
              columns={[
                {
                  id: 'member',
                  header: 'Member',
                  cell: (patient) => `${patient.last_name}, ${patient.first_name}`,
                  sortValue: (patient) => `${patient.last_name}, ${patient.first_name}`,
                },
                {
                  id: 'dob',
                  header: 'DOB',
                  cell: (patient) => formatDate(patient.date_of_birth),
                  sortValue: (patient) => patient.date_of_birth,
                },
                {
                  id: 'member_id',
                  header: 'Member ID',
                  cell: (patient) => patient.member_id ?? 'Not provided',
                  sortValue: (patient) => patient.member_id ?? '',
                },
                {
                  id: 'service_date',
                  header: 'Service Date',
                  cell: (patient) => formatDate(patient.service_date),
                  sortValue: (patient) => patient.service_date,
                },
              ]}
              emptyMessage="No patient rows were returned."
              pageSize={5}
              rowKey={(patient, index) => `${patient.last_name}-${patient.first_name}-${index}`}
              rows={previewState.response.patients.slice(0, 5)}
            />
          </Card>

          {showRowErrorDetails ? (
            <Card className="space-y-3">
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">Excluded row details</h2>
              <ul className="space-y-3 text-sm text-[var(--color-text-primary)]">
                {previewState.response.errors.map((rowError, index) => (
                  <li key={`${rowError.row}-${rowError.field}-${index}`}>
                    Row {rowError.row}
                    {rowError.field ? ` • ${rowError.field}` : ''} • {rowError.message}
                    {rowError.suggestion ? (
                      <span className="text-[var(--color-text-secondary)]"> • {rowError.suggestion}</span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}
        </div>
      ) : (
        <div className="space-y-6">
          <Card className="grid gap-4 md:grid-cols-4">
            <SummaryCard
              label="Transaction Type"
              value={previewState.preview.transactionType.toUpperCase()}
            />
            <SummaryCard label="Segment Count" value={String(previewState.preview.segmentCount)} />
            <SummaryCard label="Sender" value={previewState.preview.senderId} />
            <SummaryCard label="Receiver" value={previewState.preview.receiverId} />
          </Card>

          <Card className="space-y-4">
            <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">Detected subscribers</h2>
            {previewState.preview.subscriberNames.length === 0 ? (
              <p className="text-sm text-[var(--color-text-secondary)]">
                No subscriber names were detected in the preview pass.
              </p>
            ) : (
              <ul className="space-y-2 text-sm text-[var(--color-text-primary)]">
                {previewState.preview.subscriberNames.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <Button onClick={() => navigate('/')} variant="secondary">
          Cancel
        </Button>
        <Button disabled={isProcessing} onClick={() => void handleProcess(false)} variant="primary">
          Process
        </Button>
      </div>
    </AppShell>
  )
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-5">
      <p className="text-caption font-medium uppercase tracking-[0.04em] text-[var(--color-text-tertiary)]">
        {label}
      </p>
      <p className="mt-3 break-all text-2xl font-semibold text-[var(--color-text-primary)]">{value}</p>
    </Card>
  )
}

function isMemberIdWarning(warning: WarningMessage): boolean {
  return warning.field === 'member_id'
}
