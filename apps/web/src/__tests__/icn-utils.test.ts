import { describe, it, expect } from 'vitest'
import { nextIsaControlNumber, MAX_ISA_CONTROL_NUMBER, MIN_ISA_CONTROL_NUMBER } from '../utils/constants'

describe('nextIsaControlNumber', () => {
  it('returns 1 when last is null', () => {
    expect(nextIsaControlNumber(null)).toBe(1)
  })

  it('increments by 1 when last is within range', () => {
    expect(nextIsaControlNumber(1)).toBe(2)
    expect(nextIsaControlNumber(100)).toBe(101)
    expect(nextIsaControlNumber(999)).toBe(1000)
  })

  it('wraps to 1 when last is at max', () => {
    expect(nextIsaControlNumber(MAX_ISA_CONTROL_NUMBER)).toBe(MIN_ISA_CONTROL_NUMBER)
  })

  it('wraps to 1 when last exceeds max', () => {
    expect(nextIsaControlNumber(MAX_ISA_CONTROL_NUMBER + 1)).toBe(MIN_ISA_CONTROL_NUMBER)
  })

  it('handles edge case at boundary', () => {
    expect(nextIsaControlNumber(999_999_998)).toBe(999_999_999)
  })
})
