import { describe, it, expect } from 'vitest'

import type { GenerateResponse } from '../types/api'
import {
  highestIsa13,
  nextIsaControlNumber,
  MAX_ISA_CONTROL_NUMBER,
  MIN_ISA_CONTROL_NUMBER,
} from '../utils/constants'

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

describe('highestIsa13', () => {
  it('falls back to the top-level control number for a single-file response', () => {
    const response = generateResponse({
      controlNumbers: { isa13: '000000042', gs06: '42', st02Range: [] },
      archiveEntries: [],
    })

    const highestIcn = highestIsa13(response)

    expect(highestIcn).toBe(42)
    expect(nextIsaControlNumber(highestIcn)).toBe(43)
  })

  it('returns the highest archive entry control number for a split response', () => {
    const response = generateResponse({
      controlNumbers: { isa13: '000000042', gs06: '42', st02Range: [] },
      archiveEntries: [
        archiveEntry('000000042'),
        archiveEntry('000000044'),
        archiveEntry('000000043'),
      ],
    })

    const highestIcn = highestIsa13(response)

    expect(highestIcn).toBe(44)
    expect(nextIsaControlNumber(highestIcn)).toBe(45)
  })

  it('returns null when every archive entry has an unparseable control number', () => {
    const response = generateResponse({
      controlNumbers: { isa13: '000000042', gs06: '42', st02Range: [] },
      archiveEntries: [archiveEntry('not-a-number'), archiveEntry('')],
    })

    expect(highestIsa13(response)).toBeNull()
  })
})

function generateResponse(overrides: Partial<GenerateResponse>): GenerateResponse {
  return {
    x12Content: 'ISA*00*...~',
    zipContentBase64: null,
    downloadFileName: 'ACME123456_270_20260412_000000042.txt',
    batchSummaryText: null,
    batchSummaryFileName: null,
    transactionCount: 1,
    segmentCount: 13,
    fileSizeBytes: 128,
    splitCount: 1,
    controlNumbers: { isa13: '000000042', gs06: '42', st02Range: [] },
    archiveEntries: [],
    manifest: null,
    errors: [],
    partial: false,
    ...overrides,
  }
}

function archiveEntry(isa13: string): GenerateResponse['archiveEntries'][number] {
  return {
    fileName: `ACME123456_270_20260412_${isa13}.txt`,
    recordRangeStart: 1,
    recordRangeEnd: 1,
    controlNumbers: { isa13, gs06: String(Number(isa13)), st02Range: [] },
  }
}
