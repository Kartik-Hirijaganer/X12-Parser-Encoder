import { describe, expect, it } from 'vitest'

import { formatDate } from '../utils/formatters'

describe('formatters', () => {
  it('formats YYYYMMDD values for display', () => {
    expect(formatDate('20260406')).toBe('04/06/2026')
  })
})
