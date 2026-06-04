import { describe, expect, it } from 'vitest'

import {
  formatStatusBarCost,
  mergeUsage,
  shouldShowStatusBarCost,
  usageFromPartial,
  ZERO
} from '../domain/usage.js'

describe('statusBarCost', () => {
  it('mergeUsage preserves cost fields when /usage omits cost_usd', () => {
    const base = {
      ...ZERO,
      calls: 3,
      cost_status: 'estimated',
      cost_usd: 0.0042,
      total: 1200
    }

    expect(
      mergeUsage(base, {
        calls: 4,
        input: 900,
        output: 400,
        total: 1300
      })
    ).toEqual({
      ...base,
      calls: 4,
      input: 900,
      output: 400,
      total: 1300
    })
  })

  it('mergeUsage ignores undefined patch values instead of clobbering', () => {
    const base = {
      ...ZERO,
      cost_usd: 0.01,
      total: 500,
      turn_cost_usd: 0.02
    }

    expect(mergeUsage(base, { cost_usd: undefined, total: 600 })).toEqual({
      ...ZERO,
      cost_usd: 0.01,
      total: 600,
      turn_cost_usd: 0.02
    })
  })

  it('usageFromPartial seeds from ZERO when only partial usage exists', () => {
    expect(usageFromPartial({ cost_usd: 0.02, total: 100 })).toEqual({
      ...ZERO,
      cost_usd: 0.02,
      total: 100
    })
  })

  it('formatStatusBarCost prefixes estimated costs with ~', () => {
    expect(formatStatusBarCost({ cost_status: 'estimated', cost_usd: 0.0042 })).toBe('~$0.0042')
    expect(formatStatusBarCost({ cost_status: 'actual', cost_usd: 0.01 })).toBe('$0.0100')
    expect(formatStatusBarCost({ cost_usd: undefined })).toBeNull()
  })

  it('shouldShowStatusBarCost requires showCost and numeric cost_usd', () => {
    expect(shouldShowStatusBarCost(true, { cost_usd: 0.01 })).toBe(true)
    expect(shouldShowStatusBarCost(false, { cost_usd: 0.01 })).toBe(false)
    expect(shouldShowStatusBarCost(true, {})).toBe(false)
  })
})
