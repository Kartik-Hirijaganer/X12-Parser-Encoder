import { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import type { GenerateResultRouteState } from '../types/workflow'
import { decodeBase64ToBlob, downloadBlob, downloadTextFile } from '../utils/downloads'
import { formatBytes } from '../utils/formatters'
import { AppShell } from '../components/layout/AppShell'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Table } from '../components/ui/Table'
import { toast } from '../components/ui/Toast'

const SEGMENT_PREVIEW_COUNT = 10

export function GenerateResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const routeState = location.state as GenerateResultRouteState | null
  const [showFullX12, setShowFullX12] = useState(false)

  const segmentPreview = useMemo(() => {
    const content = routeState?.response.x12Content
    if (!content) {
      return { previewText: '', totalSegments: 0, hasMore: false }
    }
    const segments = content.split('~').filter((segment) => segment.length > 0)
    const sliced = segments.slice(0, SEGMENT_PREVIEW_COUNT).join('~')
    const previewText = sliced.length > 0 ? `${sliced}~` : ''
    return {
      previewText,
      totalSegments: segments.length,
      hasMore: segments.length > SEGMENT_PREVIEW_COUNT,
    }
  }, [routeState?.response.x12Content])

  if (!routeState) {
    return (
      <AppShell title="Generate result unavailable">
        <Card className="space-y-4">
          <p className="text-base text-[var(--color-text-secondary)]">
            Generate a 270 from the preview step to see the output here.
          </p>
          <Button onClick={() => navigate('/')} variant="primary">
            Go Home
          </Button>
        </Card>
      </AppShell>
    )
  }

  const { response } = routeState
  const primaryDownloadName =
    response.downloadFileName ??
    (response.splitCount > 1 ? 'eligibility_batch.zip' : 'eligibility_270.txt')
  const batchSummaryFileName = response.batchSummaryFileName ?? 'submission_summary.txt'

  return (
    <AppShell
      subtitle="Review the output summary, use the generated filenames for audit trail matching, and download the X12 output or ZIP package for submission."
      title="Generate Result"
    >
      {response.partial || response.errors.length > 0 ? (
        <Banner title="Partial result" variant="warning">
          {response.errors.length === 0
            ? 'The generator returned a partial result.'
            : `${response.errors.length} row${response.errors.length === 1 ? '' : 's'} failed during generation and were excluded from the output.`}
        </Banner>
      ) : null}

      <Card className="space-y-3">
        <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
          Submission package
        </h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Recommended download name
        </p>
        <p className="rounded-[var(--radius-md)] bg-[var(--color-surface-subtle)] px-4 py-3 font-mono text-sm text-[var(--color-text-primary)]">
          {primaryDownloadName}
        </p>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Submit the output to Gainwell using the channel defined in your trading partner
          agreement, then keep the filename and ISA13 together for audit matching.
        </p>
      </Card>

      <Card className="grid gap-4 md:grid-cols-4">
        <SummaryCard label="Transactions" value={String(response.transactionCount)} />
        <SummaryCard label="Segments" value={String(response.segmentCount)} />
        <SummaryCard label="File Size" value={formatBytes(response.fileSizeBytes)} />
        <SummaryCard label="Split Count" value={String(response.splitCount)} />
      </Card>

      {response.splitCount > 1 && response.archiveEntries.length > 0 ? (
        <Card className="space-y-4">
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">Archive manifest</h2>
          <Table
            columns={[
              {
                id: 'file',
                header: 'File',
                cell: (entry) => entry.fileName,
                sortValue: (entry) => entry.fileName,
              },
              {
                id: 'range',
                header: 'Record Range',
                cell: (entry) => `${entry.recordRangeStart} - ${entry.recordRangeEnd}`,
                sortValue: (entry) => entry.recordRangeStart,
              },
              {
                id: 'isa',
                header: 'ISA13',
                cell: (entry) => entry.controlNumbers.isa13 ?? 'N/A',
                sortValue: (entry) => entry.controlNumbers.isa13 ?? '',
              },
            ]}
            pageSize={6}
            rowKey={(entry) => entry.fileName}
            rows={response.archiveEntries}
          />
        </Card>
      ) : null}

      {response.batchSummaryText ? (
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">
                Batch summary
              </h2>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
                Human-readable handoff notes for manual submission and audit trail matching.
              </p>
            </div>
            <p className="text-caption text-[var(--color-text-secondary)]">
              {batchSummaryFileName}
            </p>
          </div>
          <pre className="max-h-[var(--layout-preview-max-height)] overflow-auto rounded-[var(--radius-lg)] bg-[var(--color-surface-subtle)] p-5 font-mono text-caption leading-6 text-[var(--color-text-primary)]">
            {response.batchSummaryText}
          </pre>
        </Card>
      ) : null}

      {response.x12Content ? (
        <Card className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">Raw X12 preview</h2>
              <p className="mt-1 text-caption text-[var(--color-text-secondary)]">
                {showFullX12 || !segmentPreview.hasMore
                  ? `Showing all ${segmentPreview.totalSegments} segments`
                  : `Showing first ${SEGMENT_PREVIEW_COUNT} of ${segmentPreview.totalSegments} segments`}
              </p>
            </div>
            <p className="text-caption text-[var(--color-text-secondary)]">
              ISA13 {response.controlNumbers.isa13 ?? 'unknown'} • GS06 {response.controlNumbers.gs06 ?? 'unknown'}
            </p>
          </div>
          <pre className="max-h-[var(--layout-x12-preview-max-height)] overflow-auto rounded-[var(--radius-lg)] bg-[linear-gradient(to_bottom,var(--color-surface-dark),var(--color-surface-dark-end))] p-5 font-mono text-sm leading-6 text-[var(--color-code-text)]">
            {showFullX12 ? response.x12Content : segmentPreview.previewText || response.x12Content}
          </pre>
          {segmentPreview.hasMore ? (
            <Button
              onClick={() => setShowFullX12((current) => !current)}
              size="sm"
              variant="secondary"
            >
              {showFullX12 ? 'Collapse to first 10 segments' : 'Show full X12 content'}
            </Button>
          ) : null}
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Button
          onClick={() => {
            if (response.zipContentBase64) {
              downloadBlob(
                decodeBase64ToBlob(response.zipContentBase64, 'application/zip'),
                primaryDownloadName,
              )
              toast.success('Download started')
              return
            }

            if (response.x12Content) {
              downloadTextFile(response.x12Content, primaryDownloadName)
              toast.success('Download started')
            }
          }}
          variant="primary"
        >
          {response.splitCount > 1 ? 'Download ZIP' : 'Download X12'}
        </Button>
        <Button
          disabled={!response.batchSummaryText}
          onClick={() => {
            if (response.batchSummaryText) {
              downloadTextFile(
                response.batchSummaryText,
                batchSummaryFileName,
                'text/plain',
              )
              toast.success('Batch summary download started')
            }
          }}
          variant="secondary"
        >
          Download Batch Summary
        </Button>
        <Button
          disabled={!response.x12Content}
          onClick={async () => {
            if (response.x12Content) {
              await navigator.clipboard.writeText(response.x12Content)
              toast.success('Copied X12 to clipboard')
            }
          }}
          variant="ghost"
        >
          Copy to Clipboard
        </Button>
        <Button onClick={() => navigate('/')} variant="ghost">
          Upload Another
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
      <p className="mt-3 text-2xl font-semibold text-[var(--color-text-primary)]">{value}</p>
    </Card>
  )
}
