import { useLocation, useNavigate } from 'react-router-dom'

import type { ValidationResultRouteState } from '../types/workflow'
import { AppShell } from '../components/layout/AppShell'
import { IssueTable } from '../components/features/IssueTable'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { downloadTextFile } from '../utils/downloads'

export function ValidationResultPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const routeState = location.state as ValidationResultRouteState | null

  if (!routeState) {
    return (
      <AppShell title="Validation result unavailable">
        <Card className="space-y-4">
          <p className="text-[16px] text-[var(--color-text-secondary)]">
            Upload a 270 file from the home page to review validation results.
          </p>
          <Button onClick={() => navigate('/')} variant="primary">
            Go Home
          </Button>
        </Card>
      </AppShell>
    )
  }

  const { response } = routeState

  return (
    <AppShell
      subtitle="Issues are grouped into plain-English messages with concrete fix suggestions so the operator can correct the source data quickly."
      title="Validation Result"
    >
      <Card className="flex flex-wrap items-center justify-between gap-4">
        <div className="space-y-2">
          <p className="text-[14px] text-[var(--color-text-secondary)]">Overall status</p>
          <Badge variant={response.is_valid ? 'active' : 'inactive'}>
            {response.is_valid ? 'PASS' : 'FAIL'}
          </Badge>
        </div>
        <div className="flex gap-6">
          <Metric label="Errors" value={String(response.error_count)} />
          <Metric label="Warnings" value={String(response.warning_count)} />
        </div>
      </Card>

      <IssueTable issues={response.issues} />

      <div className="flex flex-wrap gap-3">
        <Button
          onClick={() =>
            downloadTextFile(JSON.stringify(response, null, 2), 'validation-report.json', 'application/json')
          }
          variant="primary"
        >
          Download Report (JSON)
        </Button>
        <Button onClick={() => navigate('/')} variant="secondary">
          Upload Another
        </Button>
      </div>
    </AppShell>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[13px] uppercase tracking-[0.04em] text-[var(--color-text-tertiary)]">{label}</p>
      <p className="mt-1 text-[24px] font-semibold text-[var(--color-text-primary)]">{value}</p>
    </div>
  )
}
