import { describe, expect, it } from 'vitest'

import {
  formatCostBreakdownPct,
  formatSessionCostLabel,
  formatStatusBarCostRich,
  formatUsdCompact,
  resolveCostBarTier,
  resolveStatusRuleLayout,
  shouldShowStatusBarCostRich
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

  it('formatStatusBarCostRich full tier omits tilde on session cost', () => {
    const text = formatStatusBarCostRich(usage, { mode: 'rich', width: 120 })

    expect(text).toContain('$0.23 / $5.74')
    expect(text).toContain('cw 43%')
    expect(text).toContain('7 calls')
    expect(text).toContain('12 tools')
    expect(text).not.toMatch(/~\$5\.74/)
  })

  it('formatStatusBarCostRich prefixes live turn cost with tilde', () => {
    const text = formatStatusBarCostRich(
      { ...usage, turn_cost_estimated: true, turn_cost_usd: 0.05 },
      { mode: 'rich', width: 120 }
    )

    expect(text).toContain('~$0.05 / $5.74')
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
    expect(resolveCostBarTier(72, 'rich')).toBe('full')
    expect(resolveCostBarTier(70, 'rich')).toBe('costs')
    expect(resolveCostBarTier(40, 'minimal')).toBe('session')
  })

  it('formatSessionCostLabel falls back for unknown or included pricing', () => {
    expect(formatSessionCostLabel({ cost_status: 'unknown', calls: 3 })).toBe('n/a')
    expect(formatSessionCostLabel({ cost_status: 'included', calls: 3 })).toBe('included')
    expect(formatSessionCostLabel({ calls: 0 })).toBe('$0.00')
  })

  it('formatStatusBarCostRich shows live token turn when USD is unavailable', () => {
    const text = formatStatusBarCostRich(
      {
        calls: 2,
        cost_status: 'unknown',
        turn_cost_estimated: true,
        turn_live_tokens: 1200
      },
      { mode: 'rich', width: 120 }
    )

    expect(text).toContain('~1.2K tok / n/a')
  })

  it('shouldShowStatusBarCostRich only depends on showCost', () => {
    expect(shouldShowStatusBarCostRich(true)).toBe(true)
    expect(shouldShowStatusBarCostRich(false)).toBe(false)
  })

  it('resolveStatusRuleLayout reserves width for the full cost segment', () => {
    const costLabel = formatStatusBarCostRich(usage, { mode: 'rich', width: 120 })
    const layout = resolveStatusRuleLayout({
      cols: 140,
      costBarMode: 'rich',
      cwdLabel: 'D:\\project',
      showCost: true,
      usage
    })

    expect(layout.costLabel).toBe(costLabel)
    expect(layout.leftWidth).toBe(140 - 'D:\\project'.length - 3 - costLabel.length - 3)
  })
})
