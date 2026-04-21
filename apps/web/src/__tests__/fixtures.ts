import type {
  ConvertResponse,
  EligibilityResult,
  EligibilitySummary,
  GenerateResponse,
  ParseResponse,
  ValidateResponse,
} from '../types/api'
import type { SubmitterConfig } from '../types/settings'
import { DEFAULT_SUBMITTER_CONFIG } from '../utils/constants'

export const configuredSettings: SubmitterConfig = {
  ...DEFAULT_SUBMITTER_CONFIG,
  organizationName: 'ACME HOME HEALTH',
  providerNpi: '1992753880',
  tradingPartnerId: 'ACME123456',
}

export const convertResponseFixture: ConvertResponse = {
  filename: 'eligibility.csv',
  file_type: 'csv',
  record_count: 2,
  warnings: [
    {
      row: 2,
      field: 'member_id',
      message: 'Member ID looks shorter than expected.',
      suggestion: 'Confirm the member ID before generating the 270 output.',
    },
  ],
  corrections: [
    {
      row: 2,
      field: 'last_name',
      original_value: 'smith',
      corrected_value: 'SMITH',
      message: 'Uppercased the subscriber last name.',
    },
  ],
  patients: [
    {
      last_name: 'SMITH',
      first_name: 'JOHN',
      date_of_birth: '19850115',
      gender: 'M',
      member_id: '12345678',
      ssn: null,
      service_type_code: '30',
      service_date: '20260412',
      service_date_end: null,
    },
    {
      last_name: 'DOE',
      first_name: 'JANE',
      date_of_birth: '19900210',
      gender: 'F',
      member_id: '1234',
      ssn: null,
      service_type_code: '30',
      service_date: '20260412',
      service_date_end: null,
    },
  ],
  errors: [
    {
      row: 3,
      field: 'date_of_birth',
      message: 'Date of birth could not be parsed.',
      suggestion: 'Use YYYYMMDD, YYYY-MM-DD, or MM/DD/YYYY.',
    },
  ],
}

export const eligibilityResultsFixture: EligibilityResult[] = [
  {
    member_name: 'SMITH, JOHN',
    member_id: '12345678',
    overall_status: 'active',
    eligibility_segments: [
      {
        eligibility_code: '1',
        service_type_code: '30',
        coverage_level_code: null,
        insurance_type_code: null,
        plan_coverage_description: 'DC MEDICAID FFS',
        monetary_amount: null,
        quantity: null,
        in_plan_network_indicator: null,
      },
    ],
    benefit_entities: [],
    aaa_errors: [],
  },
  {
    member_name: 'DOE, JANE',
    member_id: '87654321',
    overall_status: 'inactive',
    eligibility_segments: [],
    benefit_entities: [],
    aaa_errors: [],
  },
  {
    member_name: 'UNKNOWN, MEMBER',
    member_id: null,
    overall_status: 'error',
    eligibility_segments: [],
    benefit_entities: [],
    aaa_errors: [
      {
        code: '72',
        message: 'Invalid member ID.',
        follow_up_action_code: null,
        suggestion: 'Confirm the member ID and retry.',
      },
    ],
  },
]

export const eligibilitySummaryFixture: EligibilitySummary = {
  total: 3,
  active: 1,
  inactive: 1,
  error: 1,
  unknown: 0,
}

export const parseResponseFixture: ParseResponse = {
  filename: 'response.271',
  transaction_count: 3,
  summary: eligibilitySummaryFixture,
  payer_name: 'DC MEDICAID',
  results: eligibilityResultsFixture,
}

export const generateResponseFixture: GenerateResponse = {
  x12_content: 'ISA*00*...~',
  zip_content_base64: null,
  download_file_name: 'ACME123456_270_20260412_000000001.txt',
  batch_summary_text: `Submission Batch Summary
========================
Generated at: 2026-04-12 21:00
Trading Partner ID: ACME123456
Payer: DC MEDICAID (DCMEDICAID)
Profile: dc_medicaid
Record count: 2
Excluded rows: 1
Split count: 1
Service date range: 2026-04-12

Control numbers
---------------
- ACME123456_270_20260412_000000001.txt: ISA13 000000001, GS06 1, ST02 0001-0002

Submission reminder
-------------------
Submit this batch to Gainwell through the channel defined in your trading partner agreement, typically the web portal or SFTP.
Keep the generated filename and ISA13 control number together for audit trail matching.`,
  batch_summary_file_name: 'ACME123456_270_20260412_000000001_summary.txt',
  transaction_count: 2,
  segment_count: 24,
  file_size_bytes: 1024,
  split_count: 1,
  control_numbers: {
    isa13: '000000001',
    gs06: '1',
    st02_range: ['0001', '0002'],
  },
  archive_entries: [
    {
      file_name: 'ACME123456_270_20260412_000000001.txt',
      record_range_start: 1,
      record_range_end: 2,
      control_numbers: {
        isa13: '000000001',
        gs06: '1',
        st02_range: ['0001', '0002'],
      },
    },
  ],
  manifest: null,
  errors: [
    {
      row: 3,
      field: 'date_of_birth',
      message: 'Date of birth could not be parsed.',
      suggestion: 'Use YYYYMMDD, YYYY-MM-DD, or MM/DD/YYYY.',
    },
  ],
  partial: true,
}

export const validateResponseFixture: ValidateResponse = {
  filename: 'bad.270',
  is_valid: false,
  error_count: 1,
  warning_count: 1,
  issues: [
    {
      severity: 'error',
      level: 'snip_2',
      code: 'E201',
      message: "Row 12: Member ID '1234' is too short.",
      location: 'segment_position:12',
      segment_id: 'NM1',
      element: 'NM109',
      suggestion: 'Confirm the member ID and regenerate the file.',
      profile: 'dc_medicaid',
    },
    {
      severity: 'warning',
      level: 'snip_1',
      code: 'W101',
      message: 'Contact email was not provided.',
      location: null,
      segment_id: 'PER',
      element: null,
      suggestion: 'Add a contact email if trading partner operations require it.',
      profile: 'dc_medicaid',
    },
  ],
}
