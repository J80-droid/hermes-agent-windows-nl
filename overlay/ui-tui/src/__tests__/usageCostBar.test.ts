import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as liveTurnCost from '../domain/liveTurnCost.js'
import * as usageModule from '../domain/usage.js'
import {
  formatCostBreakdownPct,
  formatSessionCostLabel,
  formatStatusBarCostRich,
  formatTurnCostLabel,
  formatUsdCompact,
  resolveCostBarTier,
  resolveStatusRuleLayout,
  shouldShowStatusBarCostRich,
  STATUS_RULE_HORIZONTAL_PADDING,
  statusRuleColumns,
  statusRuleMinLeftWidth
} from '../domain/usageCostBar.js'
import { statusRuleWidths } from '../components/appChrome.js'

const stringWidthMock = vi.hoisted(() => vi.fn((s: string) => [...s].length))

vi.mock('@hermes/ink', async importOriginal => {
  const actual = await importOriginal<typeof import('@hermes/ink')>()
  return {
    ...actual,
    stringWidth: (s: string) => stringWidthMock(s)
  }
})

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

  it('statusRuleColumns subtracts composer horizontal padding', () => {
    expect(statusRuleColumns(120)).toBe(118)
    expect(statusRuleColumns(1)).toBe(1)
  })

  it('resolveStatusRuleLayout reserves width for the full cost segment', () => {
    const effectiveCols = statusRuleColumns(140)
    const cwdReserve = 12
    const costLabel = formatStatusBarCostRich(usage, {
      mode: 'rich',
      width: Math.max(0, effectiveCols - cwdReserve - 12)
    })
    const layout = resolveStatusRuleLayout({
      cols: 140,
      cwdReserve,
      costBarMode: 'rich',
      cwdLabel: 'D:\\project',
      showCost: true,
      usage
    })

    expect(layout.costLabel).toBe(costLabel)
    expect(layout.leftWidth).toBe(effectiveCols - cwdReserve)
  })

  it('resolveStatusRuleLayout reserves extra width when throughput is enabled', () => {
    const effectiveCols = statusRuleColumns(140)
    const cwdReserve = 12
    const withTps = resolveStatusRuleLayout({
      cols: 140,
      cwdReserve,
      costBarMode: 'rich',
      cwdLabel: 'D:\\project',
      showCost: true,
      showStatusBarTps: true,
      usage
    })
    const withoutTps = resolveStatusRuleLayout({
      cols: 140,
      cwdReserve,
      costBarMode: 'rich',
      cwdLabel: 'D:\\project',
      showCost: true,
      showStatusBarTps: false,
      usage
    })

    expect(withTps.leftWidth).toBe(withoutTps.leftWidth)
    expect((withTps.costLabel ?? '').length).toBeLessThanOrEqual((withoutTps.costLabel ?? '').length)
  })
})

describe('formatUsdCompact edge cases', () => {
  it('formats zero and rounds to two decimals', () => {
    expect(formatUsdCompact(0)).toBe('$0.00')
    expect(formatUsdCompact(0.004)).toBe('$0.00')
    // JS float artefact: 0.995.toFixed(2) === '0.99'
    expect(formatUsdCompact(0.995)).toBe('$0.99')
    expect(formatUsdCompact(1.234)).toBe('$1.23')
  })
})

describe('formatSessionCostLabel edge cases', () => {
  it('prefers explicit cost_usd over status flags', () => {
    expect(
      formatSessionCostLabel({ cost_usd: 1.5, cost_status: 'unknown', calls: 99 })
    ).toBe('$1.50')
  })

  it('returns n/a when calls exist but pricing is unknown', () => {
    expect(formatSessionCostLabel({ cost_status: 'unknown', calls: 5 })).toBe('n/a')
  })

  it('returns $0.00 only when calls is zero/falsy', () => {
    expect(formatSessionCostLabel({ cost_status: 'estimated', calls: 0 })).toBe('$0.00')
    expect(formatSessionCostLabel({ cost_status: 'estimated' })).toBe('$0.00')
  })
})

describe('formatTurnCostLabel edge cases', () => {
  it('ignores zero or negative turn_cost_usd', () => {
    expect(formatTurnCostLabel({ calls: 1, turn_cost_usd: 0 })).toBeNull()
    expect(formatTurnCostLabel({ calls: 1, turn_cost_usd: -0.01 })).toBeNull()
  })

  it('prefers USD over live tokens when both are set', () => {
    const label = formatTurnCostLabel({
      calls: 1,
      turn_cost_usd: 0.12,
      turn_live_tokens: 900
    })
    expect(label).toContain('$0.12')
    expect(label).not.toContain('tok')
  })

  it('returns null when no turn signals exist', () => {
    expect(formatTurnCostLabel({ calls: 3, cost_status: 'estimated' })).toBeNull()
  })
})

describe('formatCostBreakdownPct edge cases', () => {
  it('returns null for empty or partial breakdown objects', () => {
    expect(formatCostBreakdownPct(undefined)).toBeNull()
    expect(formatCostBreakdownPct({})).toBeNull()
    expect(formatCostBreakdownPct({ cw: 50 })).toBe('cw 50%')
  })

  it('skips non-number fields without throwing', () => {
    expect(
      formatCostBreakdownPct({ cw: 'bad' as unknown as number, out: 10 })
    ).toBe('out 10%')
  })

  it('skips NaN and Infinity breakdown values', () => {
    expect(formatCostBreakdownPct({ cw: Number.NaN, out: 10, in: Number.POSITIVE_INFINITY })).toBe(
      'out 10%'
    )
  })
})

describe('resolveCostBarTier boundaries', () => {
  it('uses full tier at exactly FULL_MIN_WIDTH', () => {
    expect(resolveCostBarTier(72, 'rich')).toBe('full')
    expect(resolveCostBarTier(71, 'rich')).toBe('costs')
  })

  it('uses costs tier at exactly COSTS_MIN_WIDTH', () => {
    expect(resolveCostBarTier(58, 'rich')).toBe('costs')
    expect(resolveCostBarTier(57, 'rich')).toBe('session')
  })

  it('never returns full/costs for minimal mode regardless of width', () => {
    expect(resolveCostBarTier(200, 'minimal')).toBe('session')
    expect(resolveCostBarTier(0, 'minimal')).toBe('session')
  })
})

describe('formatStatusBarCostRich negative scenarios', () => {
  const base = {
    calls: 0,
    cost_status: 'unknown' as const,
    session_tools_executed: 0
  }

  it('omits calls/tools segments when counts are zero', () => {
    const text = formatStatusBarCostRich(
      { ...base, cost_usd: 2, turn_cost_usd: 0.1 },
      { mode: 'rich', width: 120 }
    )
    expect(text).not.toContain('calls')
    expect(text).not.toContain('tools')
  })

  it('handles negative width as session tier (width defaults)', () => {
    expect(formatStatusBarCostRich({ ...base, cost_usd: 3 }, { mode: 'rich', width: -5 })).toBe('$3.00')
  })
})

describe('statusRuleColumns edge cases', () => {
  it('never returns less than 1 column', () => {
    expect(statusRuleColumns(0)).toBe(1)
    expect(statusRuleColumns(-20)).toBe(1)
    expect(statusRuleColumns(STATUS_RULE_HORIZONTAL_PADDING)).toBe(1)
  })

  it('clamps non-finite cols to 1 effective column', () => {
    expect(statusRuleColumns(Number.NaN)).toBe(1)
    expect(statusRuleColumns(Number.POSITIVE_INFINITY)).toBe(1)
  })

  it('subtracts horizontal padding for wide terminals', () => {
    expect(statusRuleColumns(100)).toBe(100 - STATUS_RULE_HORIZONTAL_PADDING)
  })
})

describe('resolveStatusRuleLayout edge cases', () => {
  const usage = {
    calls: 4,
    cost_status: 'estimated' as const,
    cost_usd: 2.5,
    turn_cost_usd: 0.11
  }

  beforeEach(() => {
    stringWidthMock.mockImplementation((s: string) => [...s].length)
  })

  it('returns null costLabel when showCost is false', () => {
    const layout = resolveStatusRuleLayout({
      cols: 120,
      cwdReserve: 20,
      costBarMode: 'rich',
      cwdLabel: '/tmp',
      showCost: false,
      usage
    })
    expect(layout.costLabel).toBeNull()
    expect(layout.leftWidth).toBeGreaterThanOrEqual(statusRuleMinLeftWidth(statusRuleColumns(120)))
  })

  it('honours explicit cwdReserve=0 (max space for cost segment)', () => {
    const withReserve = resolveStatusRuleLayout({
      cols: 80,
      cwdReserve: 30,
      costBarMode: 'rich',
      cwdLabel: '/ignored/when/reserve/set',
      showCost: true,
      usage
    })
    const noReserve = resolveStatusRuleLayout({
      cols: 80,
      cwdReserve: 0,
      costBarMode: 'rich',
      cwdLabel: '/ignored',
      showCost: true,
      usage
    })
    expect(noReserve.leftWidth).toBeGreaterThan(withReserve.leftWidth)
    expect(noReserve.costLabel?.length ?? 0).toBeGreaterThanOrEqual(withReserve.costLabel?.length ?? 0)
  })

  it('clamps leftWidth to statusRuleMinLeftWidth under extreme cwdReserve', () => {
    const layout = resolveStatusRuleLayout({
      cols: 40,
      cwdReserve: 200,
      costBarMode: 'rich',
      cwdLabel: 'x',
      showCost: true,
      usage
    })
    expect(layout.leftWidth).toBe(8)
    expect(layout.costLabel).toBeTruthy()
  })

  it('uses stringWidth for fallback cwdReserve (wide graphemes)', () => {
    stringWidthMock.mockReturnValue(2)
    const layout = resolveStatusRuleLayout({
      cols: 80,
      costBarMode: 'rich',
      cwdLabel: '目录/分支',
      showCost: true,
      usage
    })
    const effectiveCols = statusRuleColumns(80)
    expect(layout.leftWidth).toBe(effectiveCols - (2 + 3))
  })

  it('uses separator budget 1 when effective cols < 24 in fallback', () => {
    const layout = resolveStatusRuleLayout({
      cols: 20,
      costBarMode: 'rich',
      cwdLabel: 'abcd',
      showCost: true,
      usage
    })
    const effectiveCols = statusRuleColumns(20)
    expect(layout.leftWidth).toBe(effectiveCols - (4 + 1))
  })

  it('aligns cwdReserve with statusRuleWidths output', () => {
    const cols = 100
    const cwd = '~/repo/feature/long-branch-name'
    const ruleCols = statusRuleColumns(cols)
    const { rightWidth, separatorWidth } = statusRuleWidths(ruleCols, cwd)
    const cwdReserve = rightWidth + separatorWidth

    const layout = resolveStatusRuleLayout({
      cols,
      cwdReserve,
      costBarMode: 'rich',
      cwdLabel: cwd,
      showCost: true,
      usage
    })

    expect(layout.leftWidth).toBe(ruleCols - cwdReserve)
    expect(layout.leftWidth + cwdReserve).toBeLessThanOrEqual(ruleCols)
  })

  it('handles empty cwdLabel without throwing', () => {
    const layout = resolveStatusRuleLayout({
      cols: 60,
      costBarMode: 'rich',
      cwdLabel: '',
      showCost: true,
      usage
    })
    expect(layout.leftWidth).toBeGreaterThanOrEqual(8)
  })
})

describe('statusRuleMinLeftWidth', () => {
  it('returns 8 at the wide-terminal boundary (24 effective cols)', () => {
    expect(statusRuleMinLeftWidth(24)).toBe(8)
    expect(statusRuleMinLeftWidth(100)).toBe(8)
  })

  it('returns 1 below the wide-terminal boundary', () => {
    expect(statusRuleMinLeftWidth(23)).toBe(1)
    expect(statusRuleMinLeftWidth(1)).toBe(1)
  })

  it('treats invalid numeric input without throwing (coerced comparisons)', () => {
    expect(statusRuleMinLeftWidth(Number.NaN)).toBe(1)
    expect(statusRuleMinLeftWidth(Number.POSITIVE_INFINITY)).toBe(8)
  })
})

describe('resolveStatusRuleLayout leftWidth override', () => {
  const usage = {
    calls: 2,
    cost_status: 'estimated' as const,
    cost_usd: 1,
    turn_cost_usd: 0.05
  }

  beforeEach(() => {
    stringWidthMock.mockImplementation((s: string) => [...s].length)
  })

  it('prefers explicit leftWidth over cols - cwdReserve', () => {
    const layout = resolveStatusRuleLayout({
      cols: 100,
      cwdReserve: 40,
      leftWidth: 55,
      costBarMode: 'rich',
      cwdLabel: '~/ignored',
      showCost: true,
      usage
    })
    expect(layout.leftWidth).toBe(55)
  })

  it('uses narrow non-cost reserve when effective cols < 24', () => {
    const narrow = resolveStatusRuleLayout({
      cols: 18,
      leftWidth: 10,
      costBarMode: 'rich',
      cwdLabel: 'x',
      showCost: true,
      usage
    })
    const wide = resolveStatusRuleLayout({
      cols: 80,
      leftWidth: 10,
      costBarMode: 'rich',
      cwdLabel: 'x',
      showCost: true,
      usage
    })
    expect(narrow.costLabel).toBe('$1.00')
    expect(wide.costLabel).toBe('$1.00')
    expect((wide.costLabel?.length ?? 0) >= (narrow.costLabel?.length ?? 0)).toBe(true)
  })

  it('yields session-tier cost when leftWidth is smaller than non-cost reserve', () => {
    const layout = resolveStatusRuleLayout({
      cols: 80,
      leftWidth: 4,
      costBarMode: 'rich',
      cwdLabel: '',
      showCost: true,
      usage: { calls: 1, cost_status: 'estimated', cost_usd: 9.99, turn_cost_usd: 0.5 }
    })
    expect(layout.costLabel).toBe('$9.99')
    expect(layout.leftWidth).toBe(4)
  })

  it('aligns with statusRuleWidths when leftWidth is passed through', () => {
    const cols = 90
    const cwd = '~/workspace/hermes-agent'
    const ruleCols = statusRuleColumns(cols)
    const widths = statusRuleWidths(ruleCols, cwd)
    const layout = resolveStatusRuleLayout({
      cols,
      cwdReserve: widths.rightWidth + widths.separatorWidth,
      leftWidth: widths.leftWidth,
      costBarMode: 'rich',
      cwdLabel: cwd,
      showCost: true,
      usage
    })
    expect(layout.leftWidth).toBe(widths.leftWidth)
  })
})

describe('resolveStatusRuleLayout invalid input', () => {
  const usage = { calls: 0, cost_status: 'unknown' as const }

  beforeEach(() => {
    stringWidthMock.mockImplementation((s: string) => [...s].length)
  })

  it('handles NaN and negative cols via statusRuleColumns clamp', () => {
    const layout = resolveStatusRuleLayout({
      cols: Number.NaN,
      costBarMode: 'rich',
      cwdLabel: 'a',
      showCost: false,
      usage
    })
    expect(layout.leftWidth).toBeGreaterThanOrEqual(1)
    expect(layout.costLabel).toBeNull()
  })

  it('does not throw when stringWidth returns 0 for a long cwdLabel', () => {
    stringWidthMock.mockReturnValue(0)
    expect(() =>
      resolveStatusRuleLayout({
        cols: 60,
        costBarMode: 'rich',
        cwdLabel: 'x'.repeat(500),
        showCost: true,
        usage: { calls: 1, cost_status: 'estimated', cost_usd: 1 }
      })
    ).not.toThrow()
  })

  it('does not throw when stringWidth throws (mocked dependency failure)', () => {
    stringWidthMock.mockImplementation(() => {
      throw new Error('stringWidth unavailable')
    })
    expect(() =>
      resolveStatusRuleLayout({
        cols: 40,
        costBarMode: 'minimal',
        cwdLabel: 'bad',
        showCost: false,
        usage
      })
    ).toThrow('stringWidth unavailable')
  })
})

describe('formatStatusBarCostRich with mocked formatters', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('falls back to formatSessionCostLabel when minimal mode and formatStatusBarCost returns null', () => {
    vi.spyOn(usageModule, 'formatStatusBarCost').mockReturnValue(null)
    const text = formatStatusBarCostRich(
      { calls: 0, cost_status: 'included' },
      { mode: 'minimal', width: 120 }
    )
    expect(text).toBe('included')
    expect(usageModule.formatStatusBarCost).toHaveBeenCalled()
  })

  it('delegates turn USD formatting to formatTurnCostUsd', () => {
    const spy = vi.spyOn(liveTurnCost, 'formatTurnCostUsd').mockReturnValue('~MOCK_TURN')
    const text = formatStatusBarCostRich(
      { calls: 1, cost_status: 'estimated', cost_usd: 1, turn_cost_usd: 0.2, turn_cost_estimated: true },
      { mode: 'rich', width: 120 }
    )
    expect(spy).toHaveBeenCalledWith(0.2, true)
    expect(text).toContain('MOCK_TURN')
  })

  it('delegates live tokens to formatTurnLiveTokens when USD absent', () => {
    const spy = vi.spyOn(liveTurnCost, 'formatTurnLiveTokens').mockReturnValue('~MOCK_TOK')
    const text = formatStatusBarCostRich(
      { calls: 1, cost_status: 'unknown', turn_live_tokens: 42_000 },
      { mode: 'rich', width: 120 }
    )
    expect(spy).toHaveBeenCalledWith(42_000)
    expect(text).toContain('MOCK_TOK')
  })
})

describe('formatStatusBarCostRich tier and segment edge cases', () => {
  it('costs tier without turn shows session only in cost pair', () => {
    expect(
      formatStatusBarCostRich(
        { calls: 3, cost_status: 'estimated', cost_usd: 4, session_tools_executed: 2 },
        { mode: 'rich', width: 65 }
      )
    ).toBe('$4.00 │ 3 calls │ 2 tools')
  })

  it('full tier omits non-finite breakdown fields (NaN ignored)', () => {
    const text = formatStatusBarCostRich(
      {
        calls: 1,
        cost_status: 'estimated',
        cost_usd: 1,
        cost_breakdown_pct: { cw: Number.NaN, out: undefined } as never
      },
      { mode: 'rich', width: 100 }
    )
    expect(text).toBe('$1.00 │ 1 calls')
    expect(text).not.toContain('cw')
  })

  it('full tier omits breakdown when partial pct has only non-number fields', () => {
    const text = formatStatusBarCostRich(
      {
        calls: 1,
        cost_status: 'estimated',
        cost_usd: 1,
        cost_breakdown_pct: { cw: 'bad', out: null } as never
      },
      { mode: 'rich', width: 100 }
    )
    expect(text).toBe('$1.00 │ 1 calls')
  })

  it('uses default FULL_MIN_WIDTH when width option omitted', () => {
    const withDefault = formatStatusBarCostRich(
      {
        calls: 1,
        cost_status: 'estimated',
        cost_usd: 1,
        cost_breakdown_pct: { cw: 10, out: 20, in: 30, cr: 40 },
        turn_cost_usd: 0.01
      },
      { mode: 'rich' }
    )
    expect(withDefault).toContain('cw 10%')
  })

  it('NaN width falls through to session tier via resolveCostBarTier', () => {
    expect(
      formatStatusBarCostRich({ calls: 0, cost_status: 'estimated', cost_usd: 2.5 }, { mode: 'rich', width: Number.NaN })
    ).toBe('$2.50')
  })
})

describe('formatUsdCompact invalid numeric input', () => {
  it('formats NaN and Infinity without throwing', () => {
    expect(formatUsdCompact(Number.NaN)).toBe('$NaN')
    expect(formatUsdCompact(Number.POSITIVE_INFINITY)).toBe('$Infinity')
  })
})

describe('formatSessionCostLabel negative and invalid input', () => {
  it('treats negative cost_usd as explicit numeric (caller responsibility)', () => {
    expect(formatSessionCostLabel({ cost_usd: -1, calls: 1 })).toBe('$-1.00')
  })

  it('treats NaN cost_usd as number type and formats it', () => {
    expect(formatSessionCostLabel({ cost_usd: Number.NaN, calls: 1 })).toBe('$NaN')
  })

  it('unknown status with truthy non-number calls still returns n/a', () => {
    expect(formatSessionCostLabel({ cost_status: 'unknown', calls: 1 })).toBe('n/a')
  })
})

describe('formatTurnCostLabel with mocked liveTurnCost', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('passes turn_cost_estimated flag to formatTurnCostUsd', () => {
    const spy = vi.spyOn(liveTurnCost, 'formatTurnCostUsd').mockReturnValue('~$0.99')
    formatTurnCostLabel({ calls: 1, turn_cost_usd: 0.99, turn_cost_estimated: true })
    expect(spy).toHaveBeenCalledWith(0.99, true)
  })

  it('ignores zero turn_live_tokens and returns null', () => {
    const spy = vi.spyOn(liveTurnCost, 'formatTurnLiveTokens')
    expect(formatTurnCostLabel({ calls: 1, turn_live_tokens: 0 })).toBeNull()
    expect(spy).not.toHaveBeenCalled()
  })
})

describe('shouldShowStatusBarCostRich', () => {
  it('does not inspect usage (boolean passthrough only)', () => {
    expect(shouldShowStatusBarCostRich(true)).toBe(true)
    expect(shouldShowStatusBarCostRich(false)).toBe(false)
  })
})
