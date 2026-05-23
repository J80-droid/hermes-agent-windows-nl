import { describe, expect, it } from 'vitest'

import {
  formatCostBreakdownPct,
  formatStatusBarCostRich,
  formatUsdCompact,
  resolveCostBarTier
} from '../domain/usageCostBar.js'

describe('usageCostBar', () => {
  const usage = {
    calls: 7,
    cost_breakdown_pct: { cw: 43, out: 40, in: 16, cr: 1 },
    cost_status: 'estimated',
    cost_usd: 5.74,
    session_tools_executed: 12,
    turn_cost_usd: 0.23
  }

  it('formatUsdCompact uses two decimals without tilde', () => {
    expect(formatUsdCompact(0.23)).toBe('$0.23')
    expect(formatUsdCompact(5.74)).toBe('$5.74')
  })

  it('formatCostBreakdownPct orders cw/out/in/cr', () => {
    expect(formatCostBreakdownPct(usage.cost_breakdown_pct)).toBe('cw 43% │ out 40% │ in 16% │ cr 1%')
  })

  it('formatStatusBarCostRich full tier omits tilde', () => {
    const text = formatStatusBarCostRich(usage, { mode: 'rich', width: 120 })

    expect(text).toContain('$0.23 / $5.74')
    expect(text).toContain('cw 43%')
    expect(text).toContain('7 calls')
    expect(text).toContain('12 tools')
    expect(text).not.toContain('~')
  })

  it('formatStatusBarCostRich costs tier drops breakdown', () => {
    expect(formatStatusBarCostRich(usage, { mode: 'rich', width: 70 })).toBe(
      '$0.23 / $5.74 │ 7 calls │ 12 tools'
    )
  })

  it('formatStatusBarCostRich session tier shows session only', () => {
    expect(formatStatusBarCostRich(usage, { mode: 'rich', width: 40 })).toBe('$5.74')
  })

  it('formatStatusBarCostRich minimal mode keeps legacy formatter', () => {
    expect(formatStatusBarCostRich(usage, { mode: 'minimal', width: 120 })).toBe('~$5.7400')
  })

  it('resolveCostBarTier respects mode', () => {
    expect(resolveCostBarTier(120, 'rich')).toBe('full')
    expect(resolveCostBarTier(70, 'rich')).toBe('costs')
    expect(resolveCostBarTier(40, 'minimal')).toBe('session')
  })
})
