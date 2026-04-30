import { describe, expect, it } from 'vitest'

import { splitPlanDescription } from '../utils/plan'

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
})
