import { describe, expect, it } from 'vitest'

import { formatDate, formatStatusLabel, statusVariantFromValue } from '../utils/formatters'

describe('formatters', () => {
  it('formats YYYYMMDD values for display', () => {
    expect(formatDate('20260406')).toBe('04/06/2026')
  })

  it('formats dashboard status labels', () => {
    expect(formatStatusLabel('not_found')).toBe('Not Found')
    expect(formatStatusLabel('unknown')).toBe('Unknown')
    expect(statusVariantFromValue('not_found')).toBe('notfound')
  })

  it('formats validation page status labels', () => {
    expect(formatStatusLabel('valid')).toBe('Valid')
    expect(formatStatusLabel('invalid')).toBe('Invalid')
    expect(statusVariantFromValue('valid')).toBe('active')
    expect(statusVariantFromValue('invalid')).toBe('inactive')
  })
})
