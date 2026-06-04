import { stringWidth } from '@hermes/ink'

import type { Usage } from '../types.js'

import { formatTurnCostUsd, formatTurnLiveTokens } from './liveTurnCost.js'
import { STATUS_RULE_TPS_RESERVE } from './statusBarThroughput.js'
import { formatStatusBarCost } from './usage.js'

export type CostBarMode = 'minimal' | 'rich'

export type CostBreakdownPct = NonNullable<Usage['cost_breakdown_pct']>

export type StatusBarCostUsage = Pick<
  Usage,
  | 'calls'
  | 'cost_breakdown_pct'
  | 'cost_status'
  | 'cost_usd'
  | 'session_tools_executed'
  | 'turn_cost_estimated'
  | 'turn_cost_usd'
  | 'turn_live_tokens'
>

const FULL_MIN_WIDTH = 72
const COSTS_MIN_WIDTH = 58

export function formatUsdCompact(amount: number): string {
  return `$${amount.toFixed(2)}`
}

export function formatSessionCostLabel(
  usage: Pick<Usage, 'calls' | 'cost_status' | 'cost_usd'>
): string {
  if (typeof usage.cost_usd === 'number') {
    return formatUsdCompact(usage.cost_usd)
  }

  if (usage.cost_status === 'included') {
    return 'included'
  }

  if (usage.cost_status === 'unknown') {
    return 'n/a'
  }

  if (!usage.calls) {
    return '$0.00'
  }

  return 'n/a'
}

export function formatTurnCostLabel(usage: StatusBarCostUsage): string | null {
  if (typeof usage.turn_cost_usd === 'number' && usage.turn_cost_usd > 0) {
    return formatTurnCostUsd(usage.turn_cost_usd, Boolean(usage.turn_cost_estimated))
  }

  if (typeof usage.turn_live_tokens === 'number' && usage.turn_live_tokens > 0) {
    return formatTurnLiveTokens(usage.turn_live_tokens)
  }

  return null
}

export function formatCostBreakdownPct(pct: CostBreakdownPct | undefined): string | null {
  if (!pct) {
    return null
  }

  const parts: string[] = []

  if (typeof pct.cw === 'number' && Number.isFinite(pct.cw)) {
    parts.push(`cw ${pct.cw}%`)
  }
  if (typeof pct.out === 'number' && Number.isFinite(pct.out)) {
    parts.push(`out ${pct.out}%`)
  }
  if (typeof pct.in === 'number' && Number.isFinite(pct.in)) {
    parts.push(`in ${pct.in}%`)
  }
  if (typeof pct.cr === 'number' && Number.isFinite(pct.cr)) {
    parts.push(`cr ${pct.cr}%`)
  }

  return parts.length ? parts.join(' │ ') : null
}

export function resolveCostBarTier(width: number, mode: CostBarMode): 'costs' | 'full' | 'session' {
  if (mode !== 'rich') {
    return 'session'
  }

  if (width >= FULL_MIN_WIDTH) {
    return 'full'
  }

  if (width >= COSTS_MIN_WIDTH) {
    return 'costs'
  }

  return 'session'
}

export function formatStatusBarCostRich(
  usage: StatusBarCostUsage,
  opts: { mode?: CostBarMode; width?: number } = {}
): string {
  const mode = opts.mode ?? 'rich'
  const width = opts.width ?? FULL_MIN_WIDTH

  if (mode === 'minimal') {
    return formatStatusBarCost(usage) ?? formatSessionCostLabel(usage)
  }

  const session = formatSessionCostLabel(usage)
  const turn = formatTurnCostLabel(usage)
  const tier = resolveCostBarTier(width, mode)

  if (tier === 'session') {
    return session
  }

  const costPair = turn ? `${turn} / ${session}` : session
  const calls = typeof usage.calls === 'number' && usage.calls > 0 ? `${usage.calls} calls` : null
  const tools =
    typeof usage.session_tools_executed === 'number' && usage.session_tools_executed > 0
      ? `${usage.session_tools_executed} tools`
      : null

  if (tier === 'costs') {
    const tail = [calls, tools].filter(Boolean).join(' │ ')

    return tail ? `${costPair} │ ${tail}` : costPair
  }

  const breakdown = formatCostBreakdownPct(usage.cost_breakdown_pct)
  const segments = [costPair, breakdown, calls, tools].filter(Boolean)

  return segments.join(' │ ')
}

export function shouldShowStatusBarCostRich(showCost: boolean): boolean {
  return showCost
}

/** Minimum left segment width; must match ``statusRuleWidths`` in appChrome. */
export function statusRuleMinLeftWidth(effectiveCols: number): number {
  return effectiveCols >= 24 ? 8 : 1
}

/** Approximate display cols for status + model before inline cost (wide terminals). */
const STATUS_RULE_NON_COST_RESERVE_WIDE = 24
const STATUS_RULE_NON_COST_RESERVE_NARROW = 6

/** ComposerPane uses ``paddingX={1}``; StatusRule must fit that inner width. */
export const STATUS_RULE_HORIZONTAL_PADDING = 2

/** Effective status-rule width inside ComposerPane (non-finite terminal cols → 1). */
export function statusRuleColumns(cols: number): number {
  if (!Number.isFinite(cols)) {
    return 1
  }
  return Math.max(1, cols - STATUS_RULE_HORIZONTAL_PADDING)
}

/**
 * Reserve width for the inline cost segment on the status rule.
 * When ``cwdReserve`` is set (from ``statusRuleWidths`` in appChrome), cost tiers
 * use display columns — not ``cwdLabel.length`` (CJK-safe via Ink ``stringWidth``).
 */
export function resolveStatusRuleLayout(opts: {
  cols: number
  /** Display columns for cwd + separator (from ``statusRuleWidths`` when known). */
  cwdReserve?: number
  /** Left box width from ``statusRuleWidths`` — keeps cost tier aligned with real layout. */
  leftWidth?: number
  costBarMode: CostBarMode
  cwdLabel: string
  showCost: boolean
  showStatusBarTps?: boolean
  usage: StatusBarCostUsage
}): { costLabel: string | null; leftWidth: number } {
  const cols = statusRuleColumns(opts.cols)
  const minLeft = statusRuleMinLeftWidth(cols)
  const cwdReserve =
    opts.cwdReserve ??
    Math.min(stringWidth(opts.cwdLabel), Math.max(0, cols - minLeft - 1)) + (cols >= 24 ? 3 : 1)
  const leftWidth = opts.leftWidth ?? Math.max(minLeft, cols - cwdReserve)
  const tpsReserve = opts.showStatusBarTps && cols >= 76 ? STATUS_RULE_TPS_RESERVE : 0
  const nonCostReserve =
    (cols >= 24 ? STATUS_RULE_NON_COST_RESERVE_WIDE : STATUS_RULE_NON_COST_RESERVE_NARROW) + tpsReserve
  const costAvailableWidth = Math.max(0, leftWidth - nonCostReserve)
  const costLabel = shouldShowStatusBarCostRich(opts.showCost)
    ? formatStatusBarCostRich(opts.usage, { mode: opts.costBarMode, width: costAvailableWidth })
    : null

  return { costLabel, leftWidth }
}
