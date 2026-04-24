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
  fileType: 'csv',
  recordCount: 2,
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
      originalValue: 'smith',
      correctedValue: 'SMITH',
      message: 'Uppercased the subscriber last name.',
    },
  ],
  patients: [
    {
      lastName: 'SMITH',
      firstName: 'JOHN',
      dateOfBirth: '19850115',
      gender: 'M',
      memberId: '12345678',
      ssn: null,
      serviceTypeCode: '30',
      serviceDate: '20260412',
      serviceDateEnd: null,
    },
    {
      lastName: 'DOE',
      firstName: 'JANE',
      dateOfBirth: '19900210',
      gender: 'F',
      memberId: '1234',
      ssn: null,
      serviceTypeCode: '30',
      serviceDate: '20260412',
      serviceDateEnd: null,
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
    memberName: 'SMITH, JOHN',
    memberId: '12345678',
    overallStatus: 'active',
    statusReason: 'Coverage on file',
    stControlNumber: '0001',
    traceNumber: 'TRACE-001',
    eligibilitySegments: [
      {
        eligibilityCode: '1',
        serviceTypeCode: '30',
        serviceTypeCodes: ['30', '1'],
        coverageLevelCode: null,
        insuranceTypeCode: null,
        planCoverageDescription: 'DC MEDICAID FFS',
        monetaryAmount: null,
        quantity: null,
        inPlanNetworkIndicator: null,
      },
    ],
    benefitEntities: [
      {
        loopIdentifier: '2120C',
        qualifier: 'PI',
        identifier: 'PLAN123',
        description: null,
        entityIdentifierCode: 'P5',
        name: 'GAINWELL PLAN SPONSOR',
        contacts: ['TE:8005550100', 'EM:plans@example.test'],
      },
    ],
    aaaErrors: [],
  },
  {
    memberName: 'DOE, JANE',
    memberId: '87654321',
    overallStatus: 'inactive',
    statusReason: 'Coverage terminated',
    stControlNumber: '0002',
    traceNumber: 'TRACE-002',
    eligibilitySegments: [],
    benefitEntities: [],
    aaaErrors: [],
  },
  {
    memberName: 'ERROR, MEMBER',
    memberId: '99999999',
    overallStatus: 'error',
    statusReason: 'Invalid member ID.',
    stControlNumber: '0003',
    traceNumber: 'TRACE-003',
    eligibilitySegments: [],
    benefitEntities: [],
    aaaErrors: [
      {
        code: '72',
        message: 'Invalid member ID.',
        followUpActionCode: null,
        suggestion: 'Confirm the member ID and retry.',
      },
    ],
  },
  {
    memberName: 'MISSING, MEMBER',
    memberId: null,
    overallStatus: 'not_found',
    statusReason: 'Subscriber not found',
    stControlNumber: '0004',
    traceNumber: 'TRACE-004',
    eligibilitySegments: [],
    benefitEntities: [],
    aaaErrors: [
      {
        code: '75',
        message: 'Subscriber not found.',
        followUpActionCode: null,
        suggestion: 'Confirm the member ID and retry.',
      },
    ],
  },
  {
    memberName: 'SUPPLEMENTAL, MEMBER',
    memberId: '55555555',
    overallStatus: 'unknown',
    statusReason: 'Additional payer information only',
    stControlNumber: '0005',
    traceNumber: 'TRACE-005',
    eligibilitySegments: [
      {
        eligibilityCode: 'R',
        serviceTypeCode: '30',
        serviceTypeCodes: ['30'],
        coverageLevelCode: null,
        insuranceTypeCode: null,
        planCoverageDescription: 'Supplemental information',
        monetaryAmount: null,
        quantity: null,
        inPlanNetworkIndicator: null,
      },
    ],
    benefitEntities: [],
    aaaErrors: [],
  },
]

export const eligibilitySummaryFixture: EligibilitySummary = {
  total: 5,
  active: 1,
  inactive: 1,
  error: 1,
  notFound: 1,
  unknown: 1,
}

export const parseResponseFixture: ParseResponse = {
  filename: 'response.271',
  sourceTransactionCount: 5,
  parsedResultCount: 5,
  parserIssueCount: 0,
  parserIssues: [],
  transactionCount: 5,
  summary: eligibilitySummaryFixture,
  payerName: 'DC MEDICAID',
  results: eligibilityResultsFixture,
}

export const generateResponseFixture: GenerateResponse = {
  x12Content: 'ISA*00*...~',
  zipContentBase64: null,
  downloadFileName: 'ACME123456_270_20260412_000000001.txt',
  batchSummaryText: `Submission Batch Summary
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
  batchSummaryFileName: 'ACME123456_270_20260412_000000001_summary.txt',
  transactionCount: 2,
  segmentCount: 24,
  fileSizeBytes: 1024,
  splitCount: 1,
  controlNumbers: {
    isa13: '000000001',
    gs06: '1',
    st02Range: ['0001', '0002'],
  },
  archiveEntries: [
    {
      fileName: 'ACME123456_270_20260412_000000001.txt',
      recordRangeStart: 1,
      recordRangeEnd: 2,
      controlNumbers: {
        isa13: '000000001',
        gs06: '1',
        st02Range: ['0001', '0002'],
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

const validationIssueFixtures = [
  {
    severity: 'error',
    level: 'snip_2',
    code: 'E201',
    message: "Row 12: Member ID '1234' is too short.",
    location: 'segment_position:12',
    segmentId: 'NM1',
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
    segmentId: 'PER',
    element: null,
    suggestion: 'Add a contact email if trading partner operations require it.',
    profile: 'dc_medicaid',
  },
] as const

export const validateResponseFixture: ValidateResponse = {
  filename: 'bad.270',
  isValid: false,
  errorCount: 1,
  warningCount: 1,
  issues: validationIssueFixtures.map((issue) => ({ ...issue })),
  patients: [
    {
      index: 0,
      transactionControlNumber: '0001',
      memberName: 'SMITH, JOHN',
      memberId: '12345678',
      serviceDate: '20260412',
      status: 'valid',
      errorCount: 0,
      warningCount: 0,
      issues: [],
    },
    {
      index: 1,
      transactionControlNumber: '0002',
      memberName: 'DOE, JANE',
      memberId: '1234',
      serviceDate: '20260412',
      status: 'invalid',
      errorCount: 1,
      warningCount: 1,
      issues: validationIssueFixtures.map((issue) => ({ ...issue })),
    },
  ],
  summary: {
    totalPatients: 2,
    validPatients: 1,
    invalidPatients: 1,
  },
}
