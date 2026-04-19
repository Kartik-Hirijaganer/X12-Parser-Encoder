import type { GenerateResponse } from '../types/api'
import type { SubmitterConfig } from '../types/settings'

export const APP_VERSION = __APP_VERSION__
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
export const SETTINGS_STORAGE_KEY = 'x12_submitter_config'
export const REQUEST_TIMEOUT_MS = 30_000
export const DEFAULT_PROFILE_NAME = 'dc_medicaid'
export const DEFAULT_TEMPLATE_NAMES = {
  csv: 'eligibility_template.csv',
  xlsx: 'eligibility_template.xlsx',
  spec: 'template_spec.md',
} as const

export const REQUIRED_SETTINGS_FIELDS: Array<keyof SubmitterConfig> = [
  'organizationName',
  'providerNpi',
  'providerEntityType',
  'tradingPartnerId',
  'payerProfile',
  'payerName',
  'payerId',
  'interchangeReceiverId',
  'receiverIdQualifier',
  'senderIdQualifier',
  'usageIndicator',
  'acknowledgmentRequested',
  'defaultServiceTypeCode',
  'defaultServiceDate',
  'maxBatchSize',
]

export const SERVICE_TYPE_OPTIONS = [
  { value: '1', label: '1 - Medical Care' },
  { value: '30', label: '30 - Health Benefit Plan Coverage' },
  { value: '33', label: '33 - Chiropractic' },
  { value: '35', label: '35 - Dental Care' },
  { value: '47', label: '47 - Hospital' },
  { value: '48', label: '48 - Hospital Inpatient' },
  { value: '50', label: '50 - Hospital Outpatient' },
  { value: '86', label: '86 - Emergency Services' },
  { value: '88', label: '88 - Pharmacy' },
  { value: '98', label: '98 - Professional Physician Visit' },
  { value: 'AL', label: 'AL - Vision' },
  { value: 'MH', label: 'MH - Mental Health' },
  { value: 'UC', label: 'UC - Urgent Care' },
] as const

function todayYyyyMmDd(): string {
  const today = new Date()
  const month = String(today.getMonth() + 1).padStart(2, '0')
  const day = String(today.getDate()).padStart(2, '0')
  return `${today.getFullYear()}${month}${day}`
}

export const MAX_ISA_CONTROL_NUMBER = 999_999_999
export const MIN_ISA_CONTROL_NUMBER = 1

export function nextIsaControlNumber(last: number | null): number {
  if (last === null || last >= MAX_ISA_CONTROL_NUMBER) return MIN_ISA_CONTROL_NUMBER
  return last + 1
}
export function highestIsa13(response: GenerateResponse): number | null {
  if (response.archive_entries.length === 0) {
    return parseIsa13(response.control_numbers.isa13)
  }

  const archiveIsaValues = response.archive_entries
    .map((entry) => parseIsa13(entry.control_numbers.isa13))
    .filter((value): value is number => value !== null)

  return archiveIsaValues.length > 0 ? Math.max(...archiveIsaValues) : null
}

function parseIsa13(value: string | null): number | null {
  if (!value || !/^\d+$/.test(value)) {
    return null
  }

  const parsed = Number(value)
  if (
    !Number.isInteger(parsed) ||
    parsed < MIN_ISA_CONTROL_NUMBER ||
    parsed > MAX_ISA_CONTROL_NUMBER
  ) {
    return null
  }

  return parsed
}
export const DEFAULT_SUBMITTER_CONFIG: SubmitterConfig = {
  organizationName: '',
  providerNpi: '',
  providerEntityType: '2',
  tradingPartnerId: '',
  providerTaxonomyCode: '',
  contactName: '',
  contactPhone: '',
  contactEmail: '',
  payerProfile: DEFAULT_PROFILE_NAME,
  payerName: 'DC MEDICAID',
  payerId: 'DCMEDICAID',
  interchangeReceiverId: 'DCMEDICAID',
  receiverIdQualifier: 'ZZ',
  senderIdQualifier: 'ZZ',
  usageIndicator: 'T',
  acknowledgmentRequested: '0',
  defaultServiceTypeCode: '30',
  defaultServiceDate: todayYyyyMmDd(),
  maxBatchSize: 5000,
  lastIsaControlNumber: null,
}
