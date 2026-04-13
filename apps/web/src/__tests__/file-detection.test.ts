import { describe, expect, it } from 'vitest'

import {
  buildX12PreviewSummary,
  detectFileKind,
  detectWorkflowFromContent,
  detectX12TransactionType,
} from '../utils/fileDetection'

const sample270 = 'ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *260412*1200*^*00501*000000001*0*T*:~GS*HS*SENDER*RECEIVER*20260412*1200*1*X*005010X279A1~ST*270*0001*005010X279A1~NM1*IL*1*SMITH*JOHN****MI*12345678~SE*4*0001~GE*1*1~IEA*1*000000001~'
const sample271 = sample270.replace('ST*270', 'ST*271')

describe('fileDetection', () => {
  it('detects file kinds from extension', () => {
    expect(detectFileKind('sheet.xlsx')).toBe('excel')
    expect(detectFileKind('input.csv')).toBe('csv')
    expect(detectFileKind('response.x12')).toBe('x12')
  })

  it('detects x12 content and transaction type from ISA content', () => {
    expect(detectWorkflowFromContent('response.txt', sample270)).toBe('validate')
    expect(detectX12TransactionType(sample271)).toBe('271')
  })

  it('builds an x12 preview summary', () => {
    const preview = buildX12PreviewSummary(sample270)

    expect(preview.segmentCount).toBeGreaterThan(0)
    expect(preview.senderId).toContain('SENDER')
    expect(preview.subscriberNames[0]).toBe('SMITH, JOHN')
  })
})
