import { AppShell } from '../components/layout/AppShell'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Table } from '../components/ui/Table'
import { DEFAULT_TEMPLATE_NAMES } from '../utils/constants'
import { templateUrl } from '../services/api'

const REQUIRED_COLUMNS = [
  {
    column: 'last_name',
    required: 'Yes',
    format: 'Text',
    example: 'SMITH',
  },
  {
    column: 'first_name',
    required: 'Yes',
    format: 'Text',
    example: 'JOHN',
  },
  {
    column: 'date_of_birth',
    required: 'Yes',
    format: 'YYYYMMDD',
    example: '19850115',
  },
  {
    column: 'gender',
    required: 'Yes',
    format: 'M / F / U',
    example: 'F',
  },
  {
    column: 'member_id',
    required: 'Conditional',
    format: '8+ digits',
    example: '12345678',
  },
  {
    column: 'ssn',
    required: 'Conditional',
    format: '9 digits',
    example: '999887777',
  },
  {
    column: 'service_type_code',
    required: 'No',
    format: 'Code',
    example: '30',
  },
  {
    column: 'service_date',
    required: 'Yes',
    format: 'YYYYMMDD',
    example: '20260412',
  },
  {
    column: 'service_date_end',
    required: 'No',
    format: 'YYYYMMDD',
    example: '20260430',
  },
] as const

export function TemplatesPage() {
  return (
    <AppShell
      subtitle="Download the canonical import templates. Provider and payer identity are configured in Settings, not embedded in the spreadsheet."
      title="Import Templates"
    >
      <section className="grid gap-6 md:grid-cols-2">
        <Card className="space-y-4">
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">Excel Template</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Recommended for non-technical users who fill in the workbook manually.
          </p>
          <Button href={templateUrl(DEFAULT_TEMPLATE_NAMES.xlsx)} variant="primary">
            Download .xlsx
          </Button>
        </Card>
        <Card className="space-y-4">
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">CSV Template</h2>
          <p className="text-sm text-[var(--color-text-secondary)]">
            Use this when data is exported from another system and mapped into the canonical headers.
          </p>
          <Button href={templateUrl(DEFAULT_TEMPLATE_NAMES.csv)} variant="primary">
            Download .csv
          </Button>
        </Card>
      </section>

      <Card className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">Required Columns</h2>
          <Button href={templateUrl(DEFAULT_TEMPLATE_NAMES.spec)} target="_blank" variant="ghost">
            Open Template Spec
          </Button>
        </div>
        <Table
          columns={[
            {
              id: 'column',
              header: 'Column',
              cell: (row) => row.column,
              sortValue: (row) => row.column,
            },
            {
              id: 'required',
              header: 'Required',
              cell: (row) => row.required,
              sortValue: (row) => row.required,
            },
            {
              id: 'format',
              header: 'Format',
              cell: (row) => row.format,
              sortValue: (row) => row.format,
            },
            {
              id: 'example',
              header: 'Example',
              cell: (row) => row.example,
              sortValue: (row) => row.example,
            },
          ]}
          pageSize={6}
          rowKey={(row) => row.column}
          rows={[...REQUIRED_COLUMNS]}
        />
      </Card>

      <Card className="space-y-4">
        <h2 className="text-xl font-semibold text-[var(--color-text-primary)]">DC Medicaid Rules</h2>
        <ul className="space-y-2 text-sm leading-6 text-[var(--color-text-primary)]">
          <li>Member ID plus at least one additional search criterion is required.</li>
          <li>Service dates cannot be in the future and cannot be older than 13 months.</li>
          <li>Generate requests above 5000 rows are automatically split into multiple interchanges.</li>
          <li>Short member IDs are warned on in preview and require operator confirmation.</li>
        </ul>
      </Card>
    </AppShell>
  )
}
