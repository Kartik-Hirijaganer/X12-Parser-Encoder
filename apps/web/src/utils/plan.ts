import type { EligibilityResult } from '../types/api'

export interface ParsedPlan {
  programName: string
  payerCode: string
  category: string
}

export function splitPlanDescription(description: string | null | undefined): ParsedPlan {
  if (!description) {
    return { programName: '', payerCode: '', category: '' }
  }

  const parts = description.split('|').map((part) => part.trim())
  if (parts.length < 3) {
    return { programName: description, payerCode: '', category: '' }
  }

  return {
    programName: parts[0],
    payerCode: parts[1],
    category: parts[2],
  }
}

export function primaryPlanDescription(result: EligibilityResult): string | null {
  for (const segment of result.eligibilitySegments) {
    if (segment.planCoverageDescription) {
      return segment.planCoverageDescription
    }
  }
  return null
}

export function planBillingNote(result: EligibilityResult): string {
  if (result.statusReason) {
    return result.statusReason
  }
  return result.aaaErrors[0]?.message ?? ''
}
