export interface WarningMessage {
  row: number | null
  field: string | null
  message: string
  suggestion: string | null
}

export interface Correction {
  row: number
  field: string
  originalValue: string | null
  correctedValue: string | null
  message: string
}

export interface RowError {
  row: number
  field: string | null
  message: string
  suggestion: string | null
}

export interface PatientRecord {
  lastName: string
  firstName: string
  dateOfBirth: string
  gender: string
  memberId: string | null
  ssn: string | null
  serviceTypeCode: string
  serviceDate: string
  serviceDateEnd: string | null
}

export interface ConvertResponse {
  filename: string
  fileType: string
  recordCount: number
  warnings: WarningMessage[]
  corrections: Correction[]
  patients: PatientRecord[]
  errors: RowError[]
}

export interface ControlNumbers {
  isa13: string | null
  gs06: string | null
  st02Range: string[]
}

export interface ArchiveEntry {
  fileName: string
  recordRangeStart: number
  recordRangeEnd: number
  controlNumbers: ControlNumbers
}

export interface GenerateResponse {
  x12Content: string | null
  zipContentBase64: string | null
  downloadFileName: string | null
  batchSummaryText: string | null
  batchSummaryFileName: string | null
  transactionCount: number
  segmentCount: number
  fileSizeBytes: number
  splitCount: number
  controlNumbers: ControlNumbers
  archiveEntries: ArchiveEntry[]
  manifest: Record<string, unknown> | null
  errors: RowError[]
  partial: boolean
}

export interface ValidationIssue {
  severity: string
  level: string
  code: string
  message: string
  location: string | null
  segmentId: string | null
  element: string | null
  suggestion: string | null
  profile: string | null
  transactionIndex?: number | null
  transactionControlNumber?: string | null
}

export interface ParserIssue {
  transactionIndex: number | null
  transactionControlNumber: string | null
  segmentId: string | null
  location: string | null
  message: string
  severity: 'error' | 'warning'
}

export interface ValidationSummary {
  totalPatients: number
  validPatients: number
  invalidPatients: number
}

export interface PatientValidationRow {
  index: number
  transactionControlNumber: string | null
  memberName: string
  memberId: string | null
  serviceDate: string | null
  status: 'valid' | 'invalid'
  errorCount: number
  warningCount: number
  issues: ValidationIssue[]
}

export interface ValidateResponse {
  filename: string
  isValid: boolean
  errorCount: number
  warningCount: number
  issues: ValidationIssue[]
  patients: PatientValidationRow[]
  summary: ValidationSummary | null
}

export interface EligibilitySegment {
  eligibilityCode: string
  serviceTypeCode: string | null
  serviceTypeCodes: string[]
  coverageLevelCode: string | null
  insuranceTypeCode: string | null
  planCoverageDescription: string | null
  monetaryAmount: string | null
  quantity: string | null
  inPlanNetworkIndicator: string | null
}

export interface BenefitEntity {
  loopIdentifier: string | null
  qualifier: string | null
  identifier: string | null
  description: string | null
  entityIdentifierCode: string | null
  name: string | null
  contacts: string[]
}

export interface AAAError {
  code: string
  message: string
  followUpActionCode: string | null
  suggestion: string | null
}

export interface EligibilitySummary {
  total: number
  active: number
  inactive: number
  error: number
  notFound: number
  unknown: number
}

export interface EligibilityResult {
  memberName: string
  memberId: string | null
  overallStatus: string
  statusReason: string | null
  stControlNumber: string | null
  traceNumber: string | null
  eligibilitySegments: EligibilitySegment[]
  benefitEntities: BenefitEntity[]
  aaaErrors: AAAError[]
}

export interface ParseResponse {
  filename: string
  sourceTransactionCount: number
  parsedResultCount: number
  parserIssueCount: number
  parserIssues: ParserIssue[]
  transactionCount: number
  summary: EligibilitySummary
  payerName: string | null
  results: EligibilityResult[]
}

export interface ProfileInfo {
  name: string
  displayName: string
  description: string
}

export interface ProfilesResponse {
  profiles: ProfileInfo[]
}

export interface ProfileDefaultsResponse {
  payerName: string
  payerId: string
  interchangeReceiverId: string
  receiverIdQualifier: string
  defaultServiceTypeCode: string
  maxBatchSize: number
}

export interface ExportWorkbookRequest {
  filename: string | null
  payerName: string | null
  summary: EligibilitySummary
  results: EligibilityResult[]
  parserIssueCount: number
  parserIssues: ParserIssue[]
}
