import { useLocation, useNavigate } from 'react-router-dom'

import type { GenerateResultRouteState } from '../types/workflow'
import { decodeBase64ToBlob, downloadBlob, downloadTextFile } from '../utils/downloads'
import { formatBytes } from '../utils/formatters'
import { AppShell } from '../components/layout/AppShell'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Table } from '../components/ui/Table'

export function GenerateResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const routeState = location.state as GenerateResultRouteState | null

  if (!routeState) {
    return (
      <AppShell title="Generate result unavailable">
        <Card className="space-y-4">
          <p className="text-[16px] text-[var(--color-text-secondary)]">
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
    response.download_file_name ??
    (response.split_count > 1 ? 'eligibility_batch.zip' : 'eligibility_270.txt')
  const batchSummaryFileName = response.batch_summary_file_name ?? 'submission_summary.txt'

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
        <h2 className="text-[20px] font-semibold text-[var(--color-text-primary)]">
          Submission package
        </h2>
        <p className="text-[14px] text-[var(--color-text-secondary)]">
          Recommended download name
        </p>
        <p className="rounded-[var(--radius-md)] bg-[var(--color-surface-subtle)] px-4 py-3 font-mono text-[14px] text-[var(--color-text-primary)]">
          {primaryDownloadName}
        </p>
        <p className="text-[14px] text-[var(--color-text-secondary)]">
          Submit the output to Gainwell using the channel defined in your trading partner
          agreement, then keep the filename and ISA13 together for audit matching.
        </p>
      </Card>

      <Card className="grid gap-4 md:grid-cols-4">
        <SummaryCard label="Transactions" value={String(response.transaction_count)} />
        <SummaryCard label="Segments" value={String(response.segment_count)} />
        <SummaryCard label="File Size" value={formatBytes(response.file_size_bytes)} />
        <SummaryCard label="Split Count" value={String(response.split_count)} />
      </Card>

      {response.split_count > 1 && response.archive_entries.length > 0 ? (
        <Card className="space-y-4">
          <h2 className="text-[20px] font-semibold text-[var(--color-text-primary)]">Archive manifest</h2>
          <Table
            columns={[
              {
                id: 'file',
                header: 'File',
                cell: (entry) => entry.file_name,
                sortValue: (entry) => entry.file_name,
              },
              {
                id: 'range',
                header: 'Record Range',
                cell: (entry) => `${entry.record_range_start} - ${entry.record_range_end}`,
                sortValue: (entry) => entry.record_range_start,
              },
              {
                id: 'isa',
                header: 'ISA13',
                cell: (entry) => entry.control_numbers.isa13 ?? 'N/A',
                sortValue: (entry) => entry.control_numbers.isa13 ?? '',
              },
            ]}
            pageSize={6}
            rowKey={(entry) => entry.file_name}
            rows={response.archive_entries}
          />
        </Card>
      ) : null}

      {response.batch_summary_text ? (
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-[20px] font-semibold text-[var(--color-text-primary)]">
                Batch summary
              </h2>
              <p className="mt-2 text-[14px] text-[var(--color-text-secondary)]">
                Human-readable handoff notes for manual submission and audit trail matching.
              </p>
            </div>
            <p className="text-[13px] text-[var(--color-text-secondary)]">
              {batchSummaryFileName}
            </p>
          </div>
          <pre className="max-h-[320px] overflow-auto rounded-[var(--radius-lg)] bg-[var(--color-surface-subtle)] p-5 font-mono text-[13px] leading-6 text-[var(--color-text-primary)]">
            {response.batch_summary_text}
          </pre>
        </Card>
      ) : null}

      {response.x12_content ? (
        <Card className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-[20px] font-semibold text-[var(--color-text-primary)]">Raw X12 preview</h2>
            <p className="text-[13px] text-[var(--color-text-secondary)]">
              ISA13 {response.control_numbers.isa13 ?? 'unknown'} • GS06 {response.control_numbers.gs06 ?? 'unknown'}
            </p>
          </div>
          <pre className="max-h-[400px] overflow-auto rounded-[var(--radius-lg)] bg-[linear-gradient(to_bottom,var(--color-surface-dark),var(--color-surface-dark-end))] p-5 font-mono text-[14px] leading-6 text-[var(--color-code-text)]">
            {response.x12_content}
          </pre>
        </Card>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <Button
          onClick={() => {
            if (response.zip_content_base64) {
              downloadBlob(
                decodeBase64ToBlob(response.zip_content_base64, 'application/zip'),
                primaryDownloadName,
              )
              return
            }

            if (response.x12_content) {
              downloadTextFile(response.x12_content, primaryDownloadName)
            }
          }}
          variant="primary"
        >
          {response.split_count > 1 ? 'Download ZIP' : 'Download X12'}
        </Button>
        <Button
          disabled={!response.batch_summary_text}
          onClick={() => {
            if (response.batch_summary_text) {
              downloadTextFile(
                response.batch_summary_text,
                batchSummaryFileName,
                'text/plain',
              )
            }
          }}
          variant="secondary"
        >
          Download Batch Summary
        </Button>
        <Button
          disabled={!response.x12_content}
          onClick={async () => {
            if (response.x12_content) {
              await navigator.clipboard.writeText(response.x12_content)
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
      <p className="text-[13px] font-medium uppercase tracking-[0.04em] text-[var(--color-text-tertiary)]">
        {label}
      </p>
      <p className="mt-3 text-[24px] font-semibold text-[var(--color-text-primary)]">{value}</p>
    </Card>
  )
}
