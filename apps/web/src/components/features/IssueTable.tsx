import type { ValidationIssue } from '../../types/api'
import { Badge } from '../ui/Badge'
import { Table } from '../ui/Table'

export function IssueTable({ issues }: { issues: ValidationIssue[] }) {
  return (
    <Table
      columns={[
        {
          id: 'severity',
          header: 'Severity',
          cell: (issue) => (
            <Badge variant={issue.severity === 'warning' ? 'warning' : 'inactive'}>
              {issue.severity === 'warning' ? 'Warning' : 'Error'}
            </Badge>
          ),
          sortValue: (issue) => issue.severity,
        },
        {
          id: 'level',
          header: 'SNIP Level',
          cell: (issue) => <Badge variant="snip">{issue.level.toUpperCase()}</Badge>,
          sortValue: (issue) => issue.level,
        },
        {
          id: 'segment',
          header: 'Segment',
          cell: (issue) => issue.segmentId ?? issue.location ?? 'Envelope',
          sortValue: (issue) => issue.segmentId ?? issue.location ?? '',
        },
        {
          id: 'message',
          header: 'Message',
          cell: (issue) => (
            <div className="space-y-1">
              <p>{issue.message}</p>
              {issue.suggestion ? (
                <p className="text-caption text-[var(--color-text-secondary)]">
                  Suggested fix: {issue.suggestion}
                </p>
              ) : null}
            </div>
          ),
          sortValue: (issue) => issue.message,
        },
      ]}
      emptyMessage="No issues were returned."
      pageSize={8}
      rowKey={(issue, index) => `${issue.level}-${issue.code}-${index}`}
      rows={issues}
    />
  )
}
