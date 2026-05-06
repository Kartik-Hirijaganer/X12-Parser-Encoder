import type { EligibilityResult, EligibilitySegment, PlanOption, PlanView } from '../types/api'

export interface ParsedPlan {
  programName: string
  payerCode: string
  category: string
}

export const PLAN_VIEW_OPTIONS: Array<{ label: string; value: PlanView }> = [
  { label: 'Agency payer: Medicaid/Gainwell', value: 'agency' },
  { label: 'Primary returned', value: 'primary' },
  { label: 'Medicare', value: 'medicare' },
  { label: 'All plans', value: 'all' },
]

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

export function planOptionsForResult(result: EligibilityResult): PlanOption[] {
  if (result.planOptions?.length) {
    return result.planOptions
  }

  return buildPlanOptions(result.eligibilitySegments)
}

export function selectedPlanOptions(result: EligibilityResult, planView: PlanView): PlanOption[] {
  const options = planOptionsForResult(result)
  if (options.length === 0) {
    return []
  }

  if (planView === 'all') {
    return options
  }

  if (planView === 'primary') {
    return [options.find((option) => option.primaryReturned) ?? options[0]]
  }

  if (planView === 'medicare') {
    const medicare = options.find((option) => option.planType === 'medicare')
    return medicare ? [medicare] : []
  }

  return [defaultPlanOption(result, options)]
}

export function primaryPlanDescription(
  result: EligibilityResult,
  planView: PlanView = 'agency',
): string | null {
  const option = selectedPlanOptions(result, planView)[0]
  if (!option) {
    return null
  }
  return [option.programName, option.payerCode, option.category].filter(Boolean).join(' | ')
}

export function planBillingNote(result: EligibilityResult): string {
  if (result.statusReason) {
    return result.statusReason
  }
  return result.aaaErrors[0]?.message ?? ''
}

function buildPlanOptions(segments: EligibilitySegment[]): PlanOption[] {
  const options: PlanOption[] = []
  for (const [sourceSegmentIndex, segment] of segments.entries()) {
    if (!segment.planCoverageDescription) {
      continue
    }

    const parsed = splitPlanDescription(segment.planCoverageDescription)
    if (!parsed.programName && !parsed.payerCode && !parsed.category) {
      continue
    }

    const planType = planTypeForSegment(segment, parsed)
    options.push({
      label: planLabel(planType, parsed.programName),
      programName: parsed.programName,
      payerCode: parsed.payerCode,
      category: parsed.category,
      insuranceTypeCode: segment.insuranceTypeCode,
      eligibilityCode: segment.eligibilityCode,
      sourceSegmentIndex,
      planType,
      agencyPreferred: planType === 'medicaid',
      primaryReturned: options.length === 0,
    })
  }
  return options
}

function defaultPlanOption(result: EligibilityResult, options: PlanOption[]): PlanOption {
  const defaultIndex = result.defaultPlanOptionIndex
  if (typeof defaultIndex === 'number' && defaultIndex >= 0 && defaultIndex < options.length) {
    return options[defaultIndex]
  }
  return options.find((option) => option.agencyPreferred) ?? options[0]
}

function planTypeForSegment(segment: EligibilitySegment, parsed: ParsedPlan): string {
  const insuranceType = segment.insuranceTypeCode?.trim().toUpperCase() ?? ''
  const text = [parsed.programName, parsed.payerCode, parsed.category].join(' ').toUpperCase()
  if (insuranceType === 'MC' || text.includes('MEDICAID')) {
    return 'medicaid'
  }
  if (['MA', 'MB', 'MP'].includes(insuranceType) || text.includes('MEDICARE')) {
    return 'medicare'
  }
  return 'other'
}

function planLabel(planType: string, programName: string): string {
  if (planType === 'medicaid') {
    return 'Medicaid/Gainwell'
  }
  if (planType === 'medicare') {
    return 'Medicare'
  }
  return programName || 'Other'
}
