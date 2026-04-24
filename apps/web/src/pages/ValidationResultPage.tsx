import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import type { PatientValidationRow, ValidationIssue } from '../types/api'
import type { ValidationResultRouteState } from '../types/workflow'
import { AppShell } from '../components/layout/AppShell'
import { IssueTable } from '../components/features/IssueTable'
import { FilterBar } from '../components/features/FilterBar'
import { PatientIssueDrawer } from '../components/features/PatientIssueDrawer'
import { PatientValidationTable } from '../components/features/PatientValidationTable'
import { Badge } from '../components/ui/Badge'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { useReducedMotionPreference } from '../hooks/useReducedMotionPreference'
import { ApiError, exportValidationWorkbook } from '../services/api'
import { downloadBlob, downloadTextFile } from '../utils/downloads'
import { cn } from '../utils/cn'

const FILTER_OPTIONS = [
  { label: 'All', value: 'all' },
  { label: 'Valid', value: 'valid' },
  { label: 'Invalid', value: 'invalid' },
] as const

type ValidationStatusFilter = (typeof FILTER_OPTIONS)[number]['value']

const TAB_OPTIONS = [
  { id: 'patients', label: 'Patients' },
  { id: 'issues', label: 'Issues' },
  { id: 'summary', label: 'Summary' },
] as const

type TabId = (typeof TAB_OPTIONS)[number]['id']

export function ValidationResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const routeState = location.state as ValidationResultRouteState | null
  const prefersReducedMotion = useReducedMotionPreference()

  const [activeTab, setActiveTab] = useState<TabId>('patients')
  const [filter, setFilter] = useState<ValidationStatusFilter>('all')
  const [search, setSearch] = useState('')
  const [selectedRow, setSelectedRow] = useState<PatientValidationRow | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [showFailureDetails, setShowFailureDetails] = useState(false)
  const deferredSearch = useDeferredValue(search)
  const exportActionsRef = useRef<HTMLDivElement | null>(null)

  const focusExportAction = useCallback(() => {
    const button = exportActionsRef.current?.querySelector<HTMLButtonElement>('button')
    button?.click()
  }, [])

  const response = routeState?.response ?? null
  const patients = useMemo(() => response?.patients ?? [], [response])
  const issues = response?.issues ?? []
  const summary = response?.summary ?? null
  const isValid = response?.isValid ?? false

  useEffect(() => {
    if (!response || !isValid) {
      return
    }
    const node = exportActionsRef.current
    if (!node) {
      return
    }
    if (typeof node.scrollIntoView === 'function') {
      node.scrollIntoView({
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
        block: 'center',
      })
    }
    const button = node.querySelector<HTMLButtonElement>('button')
    button?.focus({ preventScroll: true })
  }, [response, isValid, prefersReducedMotion])

  const derivedSummary = useMemo(() => {
    if (summary) {
      return summary
    }
    const valid = patients.filter((row) => row.status === 'valid').length
    return {
      totalPatients: patients.length,
      validPatients: valid,
      invalidPatients: patients.length - valid,
    }
  }, [patients, summary])

  const filteredPatients = useMemo(() => {
    const normalizedSearch = deferredSearch.trim().toLowerCase()
    return patients.filter((row) => {
      if (filter !== 'all' && row.status !== filter) {
        return false
      }
      if (!normalizedSearch) {
        return true
      }
      return [row.memberName, row.memberId, row.transactionControlNumber]
        .filter(Boolean)
        .some((value) => value?.toLowerCase().includes(normalizedSearch))
    })
  }, [deferredSearch, filter, patients])

  const failureSummary = useMemo(() => {
    if (!response || response.isValid) {
      return null
    }
    const errorWord = response.errorCount === 1 ? 'critical issue' : 'critical issues'
    const warningWord = response.warningCount === 1 ? 'warning' : 'warnings'
    return `${response.errorCount} ${errorWord}, ${response.warningCount} ${warningWord}.`
  }, [response])

  if (!response) {
    return (
      <AppShell title="Validation result unavailable">
        <Card className="space-y-4">
          <p className="text-base text-[var(--color-text-secondary)]">
            Upload a 270 file from the home page to review validation results.
          </p>
          <Button onClick={() => navigate('/')} variant="primary">
            Go Home
          </Button>
        </Card>
      </AppShell>
    )
  }

  async function handleExportExcel() {
    if (!response) {
      return
    }
    try {
      setExportError(null)
      const blob = await exportValidationWorkbook(response)
      const filename = (response.filename || 'validation_results').replace(/\.[^.]+$/, '')
      downloadBlob(blob, `${filename}.xlsx`)
    } catch (caught) {
      setExportError(caught instanceof ApiError ? caught.message : 'Validation export failed.')
    }
  }

  function handleSelectRow(row: PatientValidationRow) {
    setSelectedRow((current) => (current?.index === row.index ? null : row))
  }

  return (
    <AppShell
      subtitle="Review per-patient validation results, drill into issue details, and export the workbook for downstream teams."
      title="Validation Result"
    >
      {response.isValid ? (
        <Banner
          actions={
            <Button onClick={focusExportAction} size="sm" variant="primary">
              Export Excel
            </Button>
          }
          title="All patients validated successfully"
          variant="success"
        >
          {derivedSummary.totalPatients} patient{derivedSummary.totalPatients === 1 ? '' : 's'} passed every
          SNIP check. Export the workbook to share with downstream teams.
        </Banner>
      ) : (
        <Banner
          actions={
            <Button
              onClick={() => setShowFailureDetails((current) => !current)}
              size="sm"
              variant="secondary"
            >
              {showFailureDetails ? 'Hide details' : 'Show details'}
            </Button>
          }
          title="Validation failed"
          variant="error"
        >
          {failureSummary} Review the filtered rows below or export the full workbook for triage.
        </Banner>
      )}

      <Card className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-2">
          <p className="text-sm text-[var(--color-text-secondary)]">Overall status</p>
          <Badge variant={response.isValid ? 'active' : 'inactive'}>
            {response.isValid ? 'PASS' : 'FAIL'}
          </Badge>
        </div>
        <div className="flex flex-wrap gap-6">
          <Metric label="Total" value={String(derivedSummary.totalPatients)} />
          <Metric label="Valid" value={String(derivedSummary.validPatients)} />
          <Metric label="Invalid" value={String(derivedSummary.invalidPatients)} />
          <Metric label="Errors" value={String(response.errorCount)} />
          <Metric label="Warnings" value={String(response.warningCount)} />
        </div>
      </Card>

      {exportError ? <Banner variant="error">{exportError}</Banner> : null}

      {!response.isValid && !showFailureDetails ? null : (
        <Card className="space-y-5">
          <Tabs active={activeTab} onChange={setActiveTab} />

          {activeTab === 'patients' ? (
            <div className="space-y-4">
              <FilterBar
                filter={filter}
                onFilterChange={(value) => {
                  setFilter(value)
                  setSelectedRow(null)
                }}
                onSearchChange={setSearch}
                options={FILTER_OPTIONS}
                search={search}
                searchPlaceholder="Search by member name or ID"
              />
              <PatientValidationTable onSelect={handleSelectRow} rows={filteredPatients} />
              {selectedRow ? (
                <PatientIssueDrawer onClose={() => setSelectedRow(null)} row={selectedRow} />
              ) : null}
            </div>
          ) : null}

          {activeTab === 'issues' ? <IssuesTab issues={issues} /> : null}

          {activeTab === 'summary' ? (
            <SummaryTab
              errorCount={response.errorCount}
              summary={derivedSummary}
              warningCount={response.warningCount}
            />
          ) : null}
        </Card>
      )}

      <div className="flex flex-wrap gap-3" ref={exportActionsRef}>
        <Button onClick={() => void handleExportExcel()} variant="primary">
          Export Excel
        </Button>
        <Button
          onClick={() =>
            downloadTextFile(JSON.stringify(response, null, 2), 'validation-report.json', 'application/json')
          }
          variant="secondary"
        >
          Download Report (JSON)
        </Button>
        <Button onClick={() => navigate('/')} variant="ghost">
          Upload Another
        </Button>
      </div>
    </AppShell>
  )
}

function Tabs({ active, onChange }: { active: TabId; onChange: (id: TabId) => void }) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-[var(--color-border-subtle)]" role="tablist">
      {TAB_OPTIONS.map((tab) => (
        <Button
          aria-selected={active === tab.id}
          className={cn(
            'rounded-b-none rounded-t-[var(--radius-md)] border-b-2 px-4 text-sm',
            active === tab.id
              ? 'border-[var(--color-action-500)] text-[var(--color-action-500)]'
              : 'border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]',
          )}
          key={tab.id}
          onClick={() => onChange(tab.id)}
          role="tab"
          variant="quiet"
        >
          {tab.label}
        </Button>
      ))}
    </div>
  )
}

function IssuesTab({ issues }: { issues: ValidationIssue[] }) {
  return <IssueTable issues={issues} />
}

function SummaryTab({
  errorCount,
  summary,
  warningCount,
}: {
  errorCount: number
  summary: { totalPatients: number; validPatients: number; invalidPatients: number }
  warningCount: number
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <Metric label="Total Patients" value={String(summary.totalPatients)} />
      <Metric label="Valid" value={String(summary.validPatients)} />
      <Metric label="Invalid" value={String(summary.invalidPatients)} />
      <Metric label="Errors" value={String(errorCount)} />
      <Metric label="Warnings" value={String(warningCount)} />
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.04em] text-[var(--color-text-tertiary)]">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-[var(--color-text-primary)]">{value}</p>
    </div>
  )
}
