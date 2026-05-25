import { stringWidth } from '@hermes/ink'

import type { Usage } from '../types.js'

import { formatTurnCostUsd, formatTurnLiveTokens } from './liveTurnCost.js'
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

  if (typeof pct.cw === 'number') {
    parts.push(`cw ${pct.cw}%`)
  }
  if (typeof pct.out === 'number') {
    parts.push(`out ${pct.out}%`)
  }
  if (typeof pct.in === 'number') {
    parts.push(`in ${pct.in}%`)
  }
  if (typeof pct.cr === 'number') {
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

const STATUS_RULE_MIN_LEFT_WIDTH = 12

/** ComposerPane uses ``paddingX={1}``; StatusRule must fit that inner width. */
export const STATUS_RULE_HORIZONTAL_PADDING = 2

export function statusRuleColumns(cols: number): number {
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
  costBarMode: CostBarMode
  cwdLabel: string
  showCost: boolean
  usage: StatusBarCostUsage
}): { costLabel: string | null; leftWidth: number } {
  const cols = statusRuleColumns(opts.cols)
  const cwdReserve =
    opts.cwdReserve ??
    Math.min(stringWidth(opts.cwdLabel), Math.max(0, cols - STATUS_RULE_MIN_LEFT_WIDTH - 1)) +
      (cols >= 24 ? 3 : 1)
  const costAvailableWidth = Math.max(0, cols - cwdReserve - STATUS_RULE_MIN_LEFT_WIDTH)
  const costLabel = shouldShowStatusBarCostRich(opts.showCost)
    ? formatStatusBarCostRich(opts.usage, { mode: opts.costBarMode, width: costAvailableWidth })
    : null
  // Cost is rendered inside the left segment (after model), not a flex sibling.
  const leftWidth = Math.max(STATUS_RULE_MIN_LEFT_WIDTH, cols - cwdReserve)

  return { costLabel, leftWidth }
}
