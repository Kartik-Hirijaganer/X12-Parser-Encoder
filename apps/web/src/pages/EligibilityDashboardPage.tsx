import { useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'

import type { DashboardRouteState } from '../types/workflow'
import { exportEligibilityWorkbook, ApiError } from '../services/api'
import { downloadBlob } from '../utils/downloads'
import { AppShell } from '../components/layout/AppShell'
import { EligibilityDashboard } from '../components/features/EligibilityDashboard'
import { Banner } from '../components/ui/Banner'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

export function EligibilityDashboardPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const routeState = location.state as DashboardRouteState | null
  const [error, setError] = useState<string | null>(null)

  if (!routeState) {
    return (
      <AppShell title="Dashboard unavailable">
        <Card className="space-y-4">
          <p className="text-base text-[var(--color-text-secondary)]">
            Upload a 271 response from the home page to review eligibility results.
          </p>
          <Button onClick={() => navigate('/')} variant="primary">
            Go Home
          </Button>
        </Card>
      </AppShell>
    )
  }

  const dashboardState = routeState

  async function handleExport() {
    try {
      setError(null)
      const workbook = await exportEligibilityWorkbook({
        filename: 'eligibility_results.xlsx',
        payer_name: dashboardState.response.payer_name,
        summary: dashboardState.response.summary,
        results: dashboardState.response.results,
        parser_issue_count: dashboardState.response.parser_issue_count,
        parser_issues: dashboardState.response.parser_issues,
      })
      downloadBlob(workbook, 'eligibility_results.xlsx')
    } catch (caughtError) {
      setError(caughtError instanceof ApiError ? caughtError.message : 'Export failed.')
    }
  }

  return (
    <AppShell
      subtitle="Filter by status, inspect returned benefit entities, and export the structured workbook for downstream review."
      title="Eligibility Results Dashboard"
    >
      {error ? <Banner variant="error">{error}</Banner> : null}
      {dashboardState.response.parser_issue_count > 0 ? (
        <Banner title="Parser Issues" variant="warning">
          {dashboardState.response.parser_issue_count} transaction(s) could not be fully parsed. The table
          shows all recovered rows and the export includes parser issue details.
        </Banner>
      ) : null}
      <EligibilityDashboard
        onExport={() => void handleExport()}
        results={dashboardState.response.results}
        summary={dashboardState.response.summary}
      />
    </AppShell>
  )
}
