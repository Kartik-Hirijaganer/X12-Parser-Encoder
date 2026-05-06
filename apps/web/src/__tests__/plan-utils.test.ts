import { describe, expect, it } from 'vitest'

import type { EligibilityResult } from '../types/api'
import { selectedPlanOptions, splitPlanDescription } from '../utils/plan'

describe('splitPlanDescription', () => {
  it('parses pipe-delimited plan descriptions', () => {
    expect(splitPlanDescription('DC MEDICAID FFS | 853Q | BUY-IN')).toEqual({
      programName: 'DC MEDICAID FFS',
      payerCode: '853Q',
      category: 'BUY-IN',
    })
  })

  it('keeps plain descriptions in the program name', () => {
    expect(splitPlanDescription('DC MEDICAID FFS')).toEqual({
      programName: 'DC MEDICAID FFS',
      payerCode: '',
      category: '',
    })
  })

  it('returns empty fields for missing descriptions', () => {
    expect(splitPlanDescription(null)).toEqual({
      programName: '',
      payerCode: '',
      category: '',
    })
  })

  it('selects Medicaid by default while preserving Medicare and all-plan views', () => {
    const result = multiPlanResult()

    expect(selectedPlanOptions(result, 'agency')[0].payerCode).toBe('853Q')
    expect(selectedPlanOptions(result, 'primary')[0].payerCode).toBe('ON-FILE')
    expect(selectedPlanOptions(result, 'medicare')[0].payerCode).toBe('ON-FILE')
    expect(selectedPlanOptions(result, 'all').map((option) => option.payerCode)).toEqual([
      'ON-FILE',
      '853Q',
    ])
  })
})

function multiPlanResult(): EligibilityResult {
  return {
    memberName: 'PLAN, SWITCH',
    memberId: 'SUB000001',
    overallStatus: 'active',
    statusReason: 'Coverage on file',
    stControlNumber: '0001',
    traceNumber: 'TRACE000001',
    eligibilitySegments: [
      {
        eligibilityCode: '1',
        serviceTypeCode: '30',
        serviceTypeCodes: ['30'],
        coverageLevelCode: null,
        insuranceTypeCode: 'MB',
        planCoverageDescription: 'MEDICARE PRIMARY | ON-FILE | MEDICARE',
        monetaryAmount: null,
        quantity: null,
        inPlanNetworkIndicator: null,
      },
      {
        eligibilityCode: '1',
        serviceTypeCode: '30',
        serviceTypeCodes: ['30'],
        coverageLevelCode: null,
        insuranceTypeCode: 'MC',
        planCoverageDescription: 'DC MEDICAID FFS | 853Q | BUY-IN',
        monetaryAmount: null,
        quantity: null,
        inPlanNetworkIndicator: null,
      },
    ],
    benefitEntities: [],
    aaaErrors: [],
  }
}
