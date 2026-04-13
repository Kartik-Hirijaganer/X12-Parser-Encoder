export interface WarningMessage {
  row: number | null
  field: string | null
  message: string
  suggestion: string | null
}

export interface Correction {
  row: number
  field: string
  original_value: string | null
  corrected_value: string | null
  message: string
}

export interface RowError {
  row: number
  field: string | null
  message: string
  suggestion: string | null
}

export interface PatientRecord {
  last_name: string
  first_name: string
  date_of_birth: string
  gender: string
  member_id: string | null
  ssn: string | null
  service_type_code: string
  service_date: string
  service_date_end: string | null
}

export interface ConvertResponse {
  filename: string
  file_type: string
  record_count: number
  warnings: WarningMessage[]
  corrections: Correction[]
  patients: PatientRecord[]
  errors: RowError[]
}

export interface ControlNumbers {
  isa13: string | null
  gs06: string | null
  st02_range: string[]
}

export interface ArchiveEntry {
  file_name: string
  record_range_start: number
  record_range_end: number
  control_numbers: ControlNumbers
}

export interface GenerateResponse {
  x12_content: string | null
  zip_content_base64: string | null
  download_file_name: string | null
  batch_summary_text: string | null
  batch_summary_file_name: string | null
  transaction_count: number
  segment_count: number
  file_size_bytes: number
  split_count: number
  control_numbers: ControlNumbers
  archive_entries: ArchiveEntry[]
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
  segment_id: string | null
  element: string | null
  suggestion: string | null
  profile: string | null
}

export interface ValidateResponse {
  filename: string
  is_valid: boolean
  error_count: number
  warning_count: number
  issues: ValidationIssue[]
}

export interface EligibilitySegment {
  eligibility_code: string
  service_type_code: string | null
  coverage_level_code: string | null
  insurance_type_code: string | null
  plan_coverage_description: string | null
  monetary_amount: string | null
  quantity: string | null
  in_plan_network_indicator: string | null
}

export interface BenefitEntity {
  loop_identifier: string | null
  qualifier: string | null
  identifier: string
  description: string | null
}

export interface AAAError {
  code: string
  message: string
  follow_up_action_code: string | null
  suggestion: string | null
}

export interface EligibilitySummary {
  total: number
  active: number
  inactive: number
  error: number
  unknown: number
}

export interface EligibilityResult {
  member_name: string
  member_id: string | null
  overall_status: string
  eligibility_segments: EligibilitySegment[]
  benefit_entities: BenefitEntity[]
  aaa_errors: AAAError[]
}

export interface ParseResponse {
  filename: string
  transaction_count: number
  summary: EligibilitySummary
  payer_name: string | null
  results: EligibilityResult[]
}

export interface ProfileInfo {
  name: string
  display_name: string
  description: string
}

export interface ProfilesResponse {
  profiles: ProfileInfo[]
}

export interface ProfileDefaultsResponse {
  payer_name: string
  payer_id: string
  interchange_receiver_id: string
  receiver_id_qualifier: string
  default_service_type_code: string
  max_batch_size: number
}

export interface ExportWorkbookRequest {
  filename: string | null
  payer_name: string | null
  summary: EligibilitySummary
  results: EligibilityResult[]
}
