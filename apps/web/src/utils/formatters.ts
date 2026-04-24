import type { EligibilityResult } from '../types/api'

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return 'Not provided'
  }

  if (/^\d{8}$/.test(value)) {
    return `${value.slice(4, 6)}/${value.slice(6, 8)}/${value.slice(0, 4)}`
  }

  return value
}

export function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`
  }
  return `${(value / (1024 * 1024)).toFixed(2)} MB`
}

export function formatStatusLabel(value: string): string {
  switch (value) {
    case 'active':
      return 'Active'
    case 'inactive':
      return 'Inactive'
    case 'error':
      return 'Error'
    case 'not_found':
      return 'Not Found'
    case 'unknown':
      return 'Unknown'
    case 'valid':
      return 'Valid'
    case 'invalid':
      return 'Invalid'
    default:
      return value
  }
}

export function statusVariantFromValue(value: string):
  | 'active'
  | 'inactive'
  | 'warning'
  | 'notfound' {
  switch (value) {
    case 'active':
    case 'pass':
    case 'valid':
      return 'active'
    case 'inactive':
    case 'fail':
    case 'error':
    case 'invalid':
      return 'inactive'
    case 'warning':
      return 'warning'
    case 'not_found':
    case 'unknown':
      return 'notfound'
    default:
      return 'notfound'
  }
}

export function summarizePlan(result: EligibilityResult): string {
  const segment = result.eligibility_segments[0]
  if (!segment) {
    return result.aaa_errors[0]?.message ?? 'No plan details returned'
  }

  return (
    segment.plan_coverage_description ??
    segment.service_type_code ??
    segment.coverage_level_code ??
    'Coverage returned'
  )
}
